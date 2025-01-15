from datetime import datetime, timezone

class Transaction:
    def __init__(self, functionName, contractAddress, hash,  time, sender):
        self.sender = sender
        self.functionName = functionName
        self.contractAddress = contractAddress
        self.hash = hash
        self.time = datetime.now(timezone.utc)

    def __str__(self):
        return f"Transaction: {self.functionName} {self.contractAddress} {self.params} {self.hash} {self.time} {self.sender}"

    def toJson(self):
        return {
            "functionName": self.functionName,
            "contractAddress": self.contractAddress,
            "hash": "0x"+self.hash,
            "time": self.time,
            "sender": self.sender
        }