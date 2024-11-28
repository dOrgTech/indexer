from apps.homebase.abis import wrapperAbi, daoAbiGlobal, tokenAbiGlobal
from datetime import datetime
from apps.homebase.entities import ProposalStatus, Proposal, StateInContract, Txaction, Token, Member, Org, Vote
import re
from web3 import Web3


class Paper:
    ZERO_ADDRESS = "0x0000000000000000000000000000000000000000"

    def __init__(self, address, kind, web3, daos_collection, db, dao=None):
        self.address = address
        self.kind = kind
        self.contract = None
        self.dao = dao
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
        supply = 0
        batch = self.db.batch()
        for num in range(len(members)):
            m: Member = Member(
                address=members[num], personalBalance=amounts[num], delegate="", votingWeight="0")
            member_doc_ref = self.daos_collection \
                .document(org.address) \
                .collection('members') \
                .document(m.address)
            batch.set(reference=member_doc_ref, document_data=m.toJson())
            supply = supply+amounts[num]
        org.totalSupply = str(supply)
        keys = decoded_event['args']['keys']
        values = decoded_event['args']['values']
        org.registry = {keys[i]: values[i] for i in range(len(keys))}
        org.quorum = decoded_event['args']['initialAmounts'][-1]
        org.proposalThreshold = decoded_event['args']['initialAmounts'][-2]
        org.votingDuration = decoded_event['args']['initialAmounts'][-3]
        org.treasuryAddress = "0xFdEe849bA09bFE39aF1973F68bA8A1E1dE79DBF9"
        org.votingDelay = decoded_event['args']['initialAmounts'][-4]
        org.executionDelay = decoded_event['args']['executionDelay']
        token_contract = self.web3.eth.contract(
            address=org.govTokenAddress, abi=self.abi)
        org.decimals = token_contract.functions.decimals().call()
        self.daos_collection.document(org.address).set(org.toJson())
        batch.commit()
        return org.address

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
        batch.update(delegator_doc_ref, {"delegate": toDelegate})
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

    def propose(self, log, web3):
        print("starting to propose")
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
            name = type_ = desc = link = None
        p: Proposal = Proposal(name=name, org=address)
        print("making the proposal")
        p.author = proposer
        p.id = proposal_id
        p.type = type_
        p.targets = targets
        p.values = values
        p.callDatas = calldatas
        from datetime import timezone
        block_details = web3.eth.get_block(log.blockNumber)
        p.createdAt = datetime.fromtimestamp(
            block_details['timestamp'], tz=timezone.utc)
        p.votingStartsBlock = str(vote_start)
        p.votingEndsBlock = str(vote_end)
        p.externalResource = link
        print("we're getting here")
        proposal_doc_ref = self.daos_collection \
            .document(self.dao) \
            .collection('proposals') \
            .document(str(proposal_id))
        print("Made the doc ref")
        proposal_doc_ref.set(p.toJson())

    def handle_event(self, log, web3=None):
        if self.kind == "wrapper":
            self.add_dao(log)
        if self.kind == "token":
            self.delegate(log)
        if self.kind == "dao":
            print("we know it's a dao")
            self.propose(log, web3)
