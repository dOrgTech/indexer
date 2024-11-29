from datetime import datetime, timedelta
from typing import Optional, Dict, List, Union
from enum import Enum


class Member:
    def __init__(self, address, delegate, personalBalance, votingWeight) -> None:
        self.address = address
        self.delegate = delegate
        self.personalBalance = personalBalance
        self.constituents = []
        self.votingWeight = votingWeight
        self.proposalsVoted = []
        self.proposalsCreated = []

    def toJson(self):
        return {
            'address': self.address,
            'delegate': self.delegate,
            'personalBalance': str(self.personalBalance),
            'votingWeight': str(self.votingWeight),
            'constituents': self.constituents,
            'proposalsVoted': self.proposalsVoted,
            'proposalsCreated': self.proposalsCreated,
            'lastSeen': datetime.now()
        }


class ProposalStatus(Enum):
    pending = 'pending'
    active = 'active'
    passed = 'passed'
    queued = 'queued'
    executable = 'executable'
    executed = 'executed'
    expired = 'expired'
    noQuorum = 'noQuorum'
    rejected = 'rejected'


class StateInContract(Enum):
    Pending = 0
    Active = 1
    Canceled = 2
    Defeated = 3
    Succeeded = 4
    Queued = 5
    Expired = 6
    Executed = 7


class Txaction:
    def toJson(self):
        pass  # Implement as needed


class Token:
    def __init__(self, name: str, symbol: str, decimals: Optional[int]):
        self.name: str = name
        self.symbol: str = symbol
        self.decimals: Optional[int] = decimals
        self.address: Optional[str] = None

    @classmethod
    def fromJson(cls, json_data: Dict[str, Union[str, int]]):
        name = json_data['name']
        symbol = json_data['symbol']
        decimals = json_data.get('decimals')
        address = json_data.get('address')
        token = cls(name=name, symbol=symbol, decimals=decimals)
        token.address = address
        return token

    def toJson(self):
        return {
            'name': self.name,
            'symbol': self.symbol,
            'decimals': self.decimals,
            'address': self.address,
        }


class Org:
    def __init__(self, name: str, govToken: Optional[Token] = None, description: Optional[str] = None, govTokenAddress: Optional[str] = None):
        self.pollsCollection = None
        self.votesCollection = None
        self.name = name
        self.govToken = govToken
        self.description = description
        self.govTokenAddress = govTokenAddress
        self.creationDate: Optional[datetime] = None
        self.memberAddresses: Dict[str, Member] = {}
        self.symbol: Optional[str] = None
        self.decimals: Optional[int] = None
        self.proposalThreshold: Optional[str] = 0
        self.totalSupply: Optional[str] = 0
        self.nonTransferrable: bool = False
        self.treasuryAddress: Optional[str] = None
        self.registryAddress: Optional[str] = None
        self.proposals: List['Proposal'] = []
        self.proposalIDs: Optional[List[str]] = []
        self.treasuryMap: Dict[str, str] = {}
        self.registry: Dict[str, str] = {}
        self.treasury: Dict[Token, str] = {}
        self.address: Optional[str] = None
        self.holders: int = 1
        self.quorum: int = 0
        self.votingDelay: int = 0
        self.votingDuration: int = 0
        self.nativeBalance: str = "0"
        self.executionDelay: int = 0

    def toJson(self):
        return {
            'name': self.name,
            'creationDate': self.creationDate,
            'description': self.description,
            'token': self.govTokenAddress,
            'treasuryAddress': self.treasuryAddress,
            'registryAddress': self.registryAddress,
            'address': self.address,
            'holders': self.holders,
            'symbol': self.symbol,
            'decimals': self.decimals,
            'proposals': self.proposalIDs,
            'proposalThreshold': str(self.proposalThreshold),
            'registry': self.registry,
            'treasury': {token.toJson(): value for token, value in self.treasury.items()},
            'votingDelay': self.votingDelay,
            'totalSupply': self.totalSupply,
            'votingDuration': self.votingDuration,
            'executionDelay': self.executionDelay,
            'quorum': self.quorum,
            'nonTransferrable': self.nonTransferrable,
        }


class Proposal:
    def __init__(self, org: Org, name: Optional[str] = None):
        self.id: Optional[str] = ""
        self.inAppnumber: int = 0
        self.state: Optional[ProposalStatus] = None
        self.hash: str = ""
        self.org: Org = org
        self.type: Optional[str] = None
        self.name: Optional[str] = name if name else "Title of the proposal (max 80 characters)"
        self.description: Optional[str] = "(no description)"
        self.author: Optional[str] = None
        self.value: float = 0.0
        self.targets: List[str] = []
        self.values: List[str] = []
        self.callDatas: List = []
        self.callData: Optional[str] = "0x"
        self.createdAt: Optional[datetime] = None
        self.votingStarts: Optional[datetime] = None
        self.votingEnds: Optional[datetime] = None
        self.executionStarts: Optional[datetime] = None
        self.executionEnds: Optional[datetime] = None
        self.status: str = ""
        self.statusHistory: Dict[str, datetime] = {"pending": datetime.now()}
        self.turnoutPercent: int = 0
        self.votingStartsBlock: Optional[int] = None
        self.votingEndsBlock: Optional[int] = None
        self.executionStartsBlock: Optional[int] = None
        self.executionEndsBlock: Optional[int] = None
        self.inFavor: str = "0"
        self.against: str = "0"
        self.votesFor: int = 0
        self.votesAgainst: int = 0
        self.externalResource: Optional[str] = "(no link provided)"
        self.transactions: List[Txaction] = []
        self.votes: List['Vote'] = []

    def getState(self):
        # Implement this method based on your specific logic
        return 0  # Placeholder

    def retrieveStage(self):
        start = self.statusHistory.get("pending")
        if not start:
            return None
        votingDelay = timedelta(minutes=self.org.votingDelay or 0)
        votingDuration = timedelta(minutes=self.org.votingDuration or 0)
        executionDelay = timedelta(minutes=self.org.executionDelay or 0)
        activeStart = start + votingDelay
        votingEnd = activeStart + votingDuration
        totalVotes = (int(self.inFavor) + int(self.against)) * \
            (10 ** (self.org.decimals or 0))
        totalSupply = int(self.org.totalSupply or "1")
        votePercentage = totalVotes * 100 / totalSupply
        stateNr = self.getState()
        state_values = list(StateInContract)
        newStatus = state_values[stateNr]
        if newStatus == StateInContract.Pending:
            self.state = ProposalStatus.pending
        elif newStatus == StateInContract.Active:
            self.state = ProposalStatus.active
            self.statusHistory.clear()
            self.statusHistory.update(
                {"pending": start, "active": activeStart})
        elif newStatus == StateInContract.Succeeded:
            self.state = ProposalStatus.passed
            self.statusHistory.clear()
            self.statusHistory.update(
                {"pending": start, "active": activeStart, "passed": votingEnd})
        elif newStatus == StateInContract.Executed:
            self.state = ProposalStatus.executed
            executionTime = self.statusHistory.get('executed', datetime.now())
            queueTime = self.statusHistory.get('executable', votingEnd)
            self.statusHistory.clear()
            self.statusHistory.update({
                "pending": start,
                "active": activeStart,
                "passed": votingEnd,
                "executable": queueTime + executionDelay,
                "executed": executionTime
            })
        elif newStatus == StateInContract.Expired:
            self.statusHistory.clear()
            self.statusHistory.update({
                "pending": start,
                "active": activeStart,
                "passed": votingEnd,
                "expired": votingEnd + votingDuration + executionDelay
            })
            self.state = ProposalStatus.expired
        elif newStatus == StateInContract.Queued:
            queueTime = self.statusHistory.get('queued', datetime.now())
            self.statusHistory.clear()
            self.statusHistory.update({
                "pending": start,
                "active": activeStart,
                "passed": votingEnd,
                "queued": queueTime
            })
            if datetime.now() < queueTime + executionDelay:
                self.state = ProposalStatus.queued
            else:
                self.state = ProposalStatus.executable
        elif newStatus == StateInContract.Canceled:
            self.state = ProposalStatus.rejected
        elif newStatus == StateInContract.Defeated:
            if votePercentage < self.org.quorum:
                self.statusHistory.clear()
            self.statusHistory.update({
                "pending": start,
                "active": activeStart,
                "rejected": votingEnd
            })
            self.state = ProposalStatus.rejected
        return self.state

    def getRemainingTime(self):
        start = self.statusHistory.get("pending")
        if not start:
            return None
        votingDelay = timedelta(minutes=self.org.votingDelay or 0)
        votingDuration = timedelta(minutes=self.org.votingDuration or 0)
        executionDelay = timedelta(minutes=self.org.executionDelay or 0)
        activeStart = start + votingDelay
        votingEnd = activeStart + votingDuration
        now = datetime.now()
        if now < activeStart:
            return activeStart - now
        elif now < votingEnd:
            return votingEnd - now
        elif self.state == ProposalStatus.executable:
            queuedTime = self.statusHistory.get("executable", datetime.now())
            executionDeadline = queuedTime + executionDelay
            return executionDeadline - now
        return None

    def toJson(self):
        return {
            'hash': self.hash,
            'type': self.type,
            'title': self.name,
            'description': self.description,
            'author': self.author,
            'calldata': self.callData,
            'createdAt': self.createdAt if self.createdAt else None,
            'callDatas': self.callDatas,
            'targets': self.targets,
            'values': self.values,
            'statusHistory': self.statusHistory,
            'turnoutPercent': self.turnoutPercent,
            'inFavor': self.inFavor,
            'against': self.against,
            'votesFor': self.votesFor,
            'votesAgainst': self.votesAgainst,
            'externalResource': self.externalResource,
            'transactions': [tx.toJson() for tx in self.transactions],
        }


class Vote:
    def __init__(self, votingPower: str, voter: str, proposalID: str, option: int, castAt=None):
        self.voter: str = voter
        self.hash = ""
        self.proposalID: str = proposalID
        self.option: int = option
        self.reason: Optional[str] = None
        self.votingPower: str = votingPower
        self.castAt: datetime = castAt if castAt else datetime.now()

    def toJson(self):
        return {
            'weight': self.votingPower,
            'cast': self.castAt.isoformat(),
            'voter': self.voter,
            'reason': self.reason,
            'option': self.option,
            'hash': self.hash
        }
