import asyncio
from web3 import Web3
from abis import economyAbi
web3 = Web3(Web3.WebsocketProvider(
    'wss://sepolia.infura.io/v3/1081d644fc4144b587a4f762846ceede'))

# Check WebSocket connection
if web3.isConnected():
    print("WebSocket connection successful")
else:
    print("Failed to connect to WebSocket")
    exit()

# Contract address and ABI
contract_address = '0xEb6fDd3ad2916bA7abf91076E6eBa609D59f715d'
contract_abi = economyAbi  # Your contract ABI

# Connect to the contract
contract = web3.eth.contract(address=contract_address, abi=contract_abi)

# Function to handle events


def handle_event(event):
    # Extract relevant data from the event
    event_data = {
        'eventName': event['event'],
        'transactionHash': event['transactionHash'].hex(),
        'blockNumber': event['blockNumber'],
        # Add more fields as needed
    }

    # Update Firestore with the event data
    # db.collection('events').add(event_data)
    print(f"Event handled and added to Firestore: {event_data}")

# Asynchronous function to listen to events


async def log_loop(event_filter):
    while True:
        for event in event_filter.get_new_entries():
            handle_event(event)
        await asyncio.sleep(2)


def main():
    event_filter = contract.events.NewProject().createFilter(fromBlock='latest')
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(log_loop(event_filter))
    finally:
        loop.close()


if __name__ == "__main__":
    main()
