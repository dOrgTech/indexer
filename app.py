from apps.homebase.abis import wrapperAbi, daoAbiGlobal, tokenAbiGlobal
from apps.homebase.paper import Paper
from datetime import datetime
import time
from firebase_admin import initialize_app
from firebase_admin import firestore, credentials
from web3 import Web3
import re
cred = credentials.Certificate('homebase.json')
initialize_app(cred)
db = firestore.client()
networks = db.collection("contracts")
ceva = networks.document("Etherlink-Testnet").get()
wrapper_address = ceva.to_dict()['wrapper']
print("wrapper address :" + str(wrapper_address))
rpc = "https://node.ghostnet.etherlink.com"
web3 = Web3(Web3.HTTPProvider(rpc))
papers = {}
daos = []
if web3.is_connected():
    print("node connected")
else:
    print("node connection failed!")

daos_collection = db.collection('idaosEtherlink-Testnet')
docs = list(daos_collection.stream())
dao_addresses = [doc.id for doc in docs]

for doc in docs:
    obj = doc.to_dict()
    try:
        p = Paper(address=obj['token'], kind="token",
                  daos_collection=daos_collection, db=db,  web3=web3, dao=doc.id)
        dao = Paper(address=obj['address'], kind="dao",
                    daos_collection=daos_collection, db=db,  web3=web3, dao=doc.id)
    except Exception as e:
        print("one DAO contract can't parse correctly: "+str(e))
    papers.update({obj['token']: p})
    papers.update({obj['address']: dao})

event_signatures = {
    web3.keccak(text="NewDaoCreated(address,address,address[],uint256[],string,string,string,uint256,address,string[],string[])").hex(): "NewDaoCreated",
    "0x01c5013cf023a364cc49643b8f57347e398d2f0db0968edeb64e7c41bf2dfbde": "NewDaoCreated",
    "0x3134e8a2e6d97e929a7e54011ea5485d7d196dd5f0ba4d4ef95803e8e3fc257f": "DelegateChanged",
    "0x7d84a6263ae0d98d3329bd7b46bb4e8d6f98cd35a7adb45c274c8b7fd5ebd5e0": "ProposalCreated",
    "0x9a2e42fd6722813d69113e7d0079d3d940171428df7373df9c7f7617cfda2892": "ProposalQueued",
    "0x712ae1383f79ac853f8d882153778e0260ef8f03b504e2866e0593e04d2b291f": "ProposalExecuted",
    "0xb8e138887d0aa13bab447e82de9d5c1777041ecd21ca36ba824ff1e6c07ddda4": "VoteCast"
}

papers.update({wrapper_address: Paper(address=wrapper_address,
              kind="wrapper", daos_collection=daos_collection, db=db,  web3=web3)})
listening_to_addresses = [wrapper_address]
listening_to_addresses = listening_to_addresses+list(papers.keys())

counter = 0
processed_transactions = set()
heartbeat = 0
print(f"Listening for {len(event_signatures)} events on {
      len(papers.items())} contracts...")

while True:
    heartbeat += 1
    try:
        latest = web3.eth.block_number
        first = latest-4
        logs = web3.eth.get_logs({
            "fromBlock": first,
            "toBlock": latest,
            "address": listening_to_addresses,
            # "topics": [[*event_signatures.keys()], None]
        })
        for log in logs:
            tx_hash = log["transactionHash"].hex()
            if tx_hash in processed_transactions:
                print("already did this one")
                continue  # Skip duplicate
            contract_address = log["address"]
            event_signature = log["topics"][0].hex()
            event_name = event_signatures[f"0x{event_signature}"]
            print(f"Event: {event_name}, Contract: {contract_address}")
            new_contract_addresses = papers[contract_address].handle_event(
                log, func=event_name)

            if new_contract_addresses != None:

                dao_address = new_contract_addresses[0]
                token_address = new_contract_addresses[1]
                print("adding dao "+dao_address+" and token "+token_address)
                listening_to_addresses = listening_to_addresses + \
                    [dao_address] + [token_address]
                print("latest addresses added " +
                      str(listening_to_addresses[-1]+", "+str(listening_to_addresses[-2])))
                papers.update({token_address: Paper(
                    address=token_address, kind="token", daos_collection=daos_collection, db=db, dao=dao_address, web3=web3)})
                papers.update({dao_address: Paper(
                    address=dao_address, kind="dao", daos_collection=daos_collection, db=db, dao=dao_address, web3=web3)})
            processed_transactions.add(tx_hash)
    except Exception as e:
        print("something went wrong "+str(e))

    if heartbeat % 50 == 0:
        print("heartbeat: "+str(heartbeat))

    time.sleep(3)
