from apps.homebase.abis import wrapperAbi, daoAbiGlobal, tokenAbiGlobal, mint_function_abi, burn_function_abi
from datetime import datetime, timezone
from apps.homebase.entities import ProposalStatus, Proposal, StateInContract, Txaction, Token, Member, Org, Vote
import re
from web3 import Web3
from google.cloud import firestore
import codecs
from apps.generic.converting import decode_function_parameters


class Paper:
    ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

    def __init__(self, address, kind, web3, daos_collection, db, dao=None, token=None):
        self.address = address
        self.kind = kind
        self.contract = None
        self.dao = dao
        self.token: Paper = token
        self.web3 = web3
        self.daos_collection = daos_collection
        self.db = db
        if kind == "wrapper":
            self.abi = re.sub(r'\n+', ' ', wrapperAbi).strip()
        elif kind == "token":
            self.abi = re.sub(r'\n+', ' ', tokenAbiGlobal).strip()
        else:
            self.abi = re.sub(r'\n+', ' ', daoAbiGlobal).strip()

    def get_contract(self):
        if self.contract == None:
            self.contract = self.web3.eth.contract(
                address=self.address, abi=self.abi)
        return self.contract

    def get_token_contract(self):
        tokenAddress = self.token.address
        return self.web3.eth.contract(address=tokenAddress, abi=tokenAbiGlobal)

    def add_dao(self, log):
        decoded_event = self.get_contract().events.NewDaoCreated().process_log(log)
        name = decoded_event['args']['name']
        print("new dao detected: "+name)
        org: Org = Org(name=name)
        org.creationDate = datetime.now()
        org.govTokenAddress = decoded_event['args']['token']
        org.address = decoded_event['args']['dao']
        org.symbol = decoded_event['args']['symbol']
        org.registryAddress = decoded_event['args']['registry']
        org.description = decoded_event['args']['description']
        members = decoded_event['args']['initialMembers']
        amounts = decoded_event['args']['initialAmounts']
        org.holders = len(members)
        token_contract = self.web3.eth.contract(
            address=org.govTokenAddress, abi=tokenAbiGlobal)
        org.decimals = token_contract.functions.decimals().call()
        supply = 0
        batch = self.db.batch()
        for num in range(len(members)):
            m: Member = Member(
                address=members[num], personalBalance=f"{str(amounts[num])}", delegate="", votingWeight="0")
            member_doc_ref = self.daos_collection \
                .document(org.address) \
                .collection('members') \
                .document(m.address)
            batch.set(reference=member_doc_ref, document_data=m.toJson())
            supply = supply+amounts[num]
        org.totalSupply = str(supply)
        keys = decoded_event['args']['keys']
        print("lenth keys: " + str(len(keys)))
        values = decoded_event['args']['values']
        if not len(keys) > 1:
            print("it's not zero "+str(keys))

            org.registry = {keys[i]: values[i] for i in range(
                len(keys)) if keys[i] != "" and values[i] != ""}
        else:
            print("it's zero")
            org.registry = {}
        org.quorum = decoded_event['args']['initialAmounts'][-1]
        org.proposalThreshold = decoded_event['args']['initialAmounts'][-2]
        org.votingDuration = decoded_event['args']['initialAmounts'][-3]
        org.treasuryAddress = "0xFdEe849bA09bFE39aF1973F68bA8A1E1dE79DBF9"
        org.votingDelay = decoded_event['args']['initialAmounts'][-4]
        org.executionDelay = decoded_event['args']['executionDelay']
        self.daos_collection.document(org.address).set(org.toJson())
        batch.commit()
        return [org.address, org.govTokenAddress]

    def delegate(self, log):
        contract = self.get_contract()
        data = contract.events.DelegateChanged().process_log(log)
        delegator = data['args']['delegator']
        fromDelegate = data['args']['fromDelegate']
        toDelegate = data['args']['toDelegate']
        batch = self.db.batch()
        delegator_doc_ref = self.daos_collection \
            .document(self.dao) \
            .collection('members') \
            .document(delegator)
        batch.update(delegator_doc_ref, {"delegate": toDelegate, })
        if delegator != toDelegate:
            print("delegating to someone else")
            toDelegate_doc_ref = self.daos_collection \
                .document(self.dao) \
                .collection('members') \
                .document(toDelegate).collection("constituents").document(delegator)
            batch.update(toDelegate_doc_ref, {"address": delegator})

            if fromDelegate and fromDelegate != self.ZERO_ADDRESS and fromDelegate != delegator:
                fromDelegate_doc_ref = self.daos_collection \
                    .document(self.dao) \
                    .collection('members') \
                    .document(fromDelegate) \
                    .collection("constituents") \
                    .document(delegator)
                batch.delete(fromDelegate_doc_ref)
        batch.commit()
        return None

    def propose(self, log):
        event = self.get_contract().events.ProposalCreated().process_log(log)
        proposal_id = event["args"]["proposalId"]
        proposer = event["args"]["proposer"]
        address = event['address']
        targets = event["args"]["targets"]
        values = event["args"]["values"]
        signatures = event["args"]["signatures"]
        calldatas = event["args"]["calldatas"]
        vote_start = event["args"]["voteStart"]
        vote_end = event["args"]["voteEnd"]
        description = event["args"]["description"]
        parts = description.split("0|||0")
        if len(parts) > 3:
            name = parts[0]
            type_ = parts[1]
            desc = parts[2]
            link = parts[3]
        else:
            name = "(no title)"
            type_ = "registry"
            desc = description
            link = "(no link)"
        p: Proposal = Proposal(name=name, org=address)
        p.author = proposer
        p.id = proposal_id
        p.type = type_
        p.targets = targets
        p.values = list(map(str, values))
        p.description = desc
        p.callDatas = calldatas
        contract = self.get_token_contract()
        p.totalSupply = contract.functions.totalSupply().call()
        p.createdAt = datetime.now(tz=timezone.utc)
        p.votingStartsBlock = str(vote_start)
        p.votingEndsBlock = str(vote_end)
        p.externalResource = link
        proposal_doc_ref = self.daos_collection \
            .document(self.dao) \
            .collection('proposals') \
            .document(str(proposal_id))
        proposal_doc_ref.set(p.toJson())

        member_doc_ref = self.daos_collection \
            .document(self.dao) \
            .collection('members') \
            .document(str(proposer))
        member_doc_ref.update(
            {"proposalsCreated": firestore.ArrayUnion([str(proposal_id)])})

    def vote(self, log):
        event = self.get_contract().events.VoteCast().process_log(log)
        proposal_id = str(event["args"]["proposalId"])
        address = event['address']
        hash = event['transactionHash']
        voter = event["args"]["voter"]
        support = event["args"]["support"]
        weight = event["args"]["weight"]
        reason = event["args"]["reason"]
        vote: Vote = Vote(proposalID=str(proposal_id), votingPower=str(
            weight), option=support, voter=voter)
        vote.reason = reason
        vote.hash = hash
        vote_doc_ref = self.daos_collection \
            .document(self.dao) \
            .collection('proposals') \
            .document(proposal_id).collection("votes").document(voter)
        vote_doc_ref.set(vote.toJson())

        member_doc_ref = self.daos_collection \
            .document(self.dao) \
            .collection('members') \
            .document(str(voter))
        member_doc_ref.update(
            {"proposalsVoted": firestore.ArrayUnion([str(proposal_id)])})
        proposal_doc_ref = self.daos_collection \
            .document(self.dao) \
            .collection('proposals') \
            .document(proposal_id)
        ceva = proposal_doc_ref.get()
        data = ceva.to_dict()
        prop: Proposal = Proposal(name="whatever", org=None)
        prop.fromJson(data)
        if support == 1:
            prop.inFavor = str(int(prop.inFavor)+int(weight))
            prop.votesFor += 1
        elif support == 0:
            prop.against = str(int(prop.against)+int(weight))
            prop.votesAgainst += 1
        proposal_doc_ref.set(prop.toJson())

    def queue(self, log):
        event = self.get_contract().events.ProposalQueued().process_log(log)
        proposal_id = str(event['args']['proposalId'])
        proposal_doc_ref = self.daos_collection \
            .document(self.dao) \
            .collection('proposals') \
            .document(proposal_id)
        proposal_doc_ref.update(
            {"statusHistory.queued": datetime.now(tz=timezone.utc)})

    def bytes_to_int(self, byte_array):
        return int.from_bytes(byte_array, byteorder='big')

    def decode_params(self, data_bytes):
        data_without_selector = data_bytes[4:]
        param1_offset_bytes = data_without_selector[:32]
        param2_offset_bytes = data_without_selector[32:64]
        param1_offset = self.bytes_to_int(param1_offset_bytes)
        param2_offset = self.bytes_to_int(param2_offset_bytes)
        param1_length_bytes = data_without_selector[param1_offset:param1_offset + 32]
        param1_length = self.bytes_to_int(param1_length_bytes)
        param1_data_bytes = data_without_selector[param1_offset +
                                                  32:param1_offset + 32 + param1_length]
        param1_data = param1_data_bytes.decode('utf-8')
        param2_length_bytes = data_without_selector[param2_offset:param2_offset + 32]
        param2_length = self.bytes_to_int(param2_length_bytes)
        param2_data_bytes = data_without_selector[param2_offset +
                                                  32:param2_offset + 32 + param2_length]
        param2_data = param2_data_bytes.decode('utf-8')
        return param1_data, param2_data

    def execute(self, log):
        try:
            print("executing proposal ")
            event = self.get_contract().events.ProposalExecuted().process_log(log)
            proposal_id = str(event['args']['proposalId'])
            print("id: "+proposal_id)
            proposal_doc_ref = self.daos_collection \
                .document(self.dao) \
                .collection('proposals') \
                .document(proposal_id)
            ceva = proposal_doc_ref.get()
            data = ceva.to_dict()
            prop: Proposal = Proposal(name="whatever", org=None)
            prop.fromJson(data)
            prop.executionHash = str(event['transactionHash'])
            if prop.type == "registry":
                hex_string = prop.callDatas[0]
                param1, param2 = self.decode_params(hex_string)
                dao_doc_ref = self.daos_collection \
                    .document(self.dao)
                altceva = dao_doc_ref.get()
                datat = altceva.to_dict()
                registry = datat.get("registry", [])
                registry[param1] = param2
                dao_doc_ref.update({"registry": registry})
            proposal_doc_ref.update(
                {"statusHistory.executed": datetime.now(tz=timezone.utc),
                 "executionHash": str(event['transactionHash'])
                 })
            if "mint" in prop.type.lower() or "burn" in prop.type.lower():
                print("we got mint or burn")
                token_contract = self.web3.eth.contract(
                    address=Web3.to_checksum_address(prop.targets[0]), abi=tokenAbiGlobal)
                params = decode_function_parameters(
                    function_abi=mint_function_abi, data_bytes=prop.callDatas[0])
                memberAddress = Web3.to_checksum_address(params[0])
                balance = token_contract.functions.balanceOf(
                    memberAddress).call()
                member_doc_ref = self.daos_collection \
                    .document(self.dao) \
                    .collection('members') \
                    .document(memberAddress)
                member_doc_ref.update({"personalBalance": str(balance)})
                supply = token_contract.functions.totalSupply().call()
                dao_doc_ref = self.daos_collection \
                    .document(self.dao)
                dao_doc_ref.update({"totalSupply": str(supply)})

        except Exception as e:
            print("execution error "+str(e))

    def handle_event(self, log, func=None):
        if self.kind == "wrapper":
            return self.add_dao(log)
        if self.kind == "token":
            self.delegate(log)
        if self.kind == "dao":
            if func == "ProposalCreated":
                self.propose(log)
            elif func == "VoteCast":
                self.vote(log)
            elif func == "ProposalQueued":
                self.queue(log)
            elif func == "ProposalExecuted":
                self.execute(log)
