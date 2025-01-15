import re
from datetime import datetime, timezone

class Project:
    def __init__(self, address, name, contractor, arbiter, termsHash, repo, description,author=None):
        self.address = address
        self.author=author if author is not None else ""
        self.name = name
        self.contractor = contractor
        self.arbiter = arbiter
        self.termsHash = termsHash
        self.repo = repo
        self.description = description
        self.created = datetime.now(timezone.utc)
        self.is_usdt = False
        self.ruling_hash = ""
        self.contributions = {}
        self.contributors_disputing = {}
        self.contributors_releasing = {}
        self.hashed_filename = ""
        self.holding = "0"
        self.status = 0

    def serialize(self):
        return {
            "author": self.author,
            "address": self.address,
            "name": self.name,
            "contractor": self.contractor,
            "arbiter": self.arbiter,
            "termsHash": self.termsHash,
            "repo": self.repo,
            "description": self.description,
            "created": self.created,
            "isUSDT": self.is_usdt,
            "ruling_hash": self.ruling_hash,
            "contributions": self.contributions,
            "contributorsDisputing": self.contributors_disputing,
            "contributorsReleasing": self.contributors_releasing,
            "hashed_filename": self.hashed_filename,
            "holding": self.holding,
            "status": self.status
        }

    def __repr__(self):
        return f"Project(name={self.name}, address={self.address}, status={self.status})"


class ProjectEvents:
    @staticmethod
    def SetParties(log):
        return {
            "contractor": log["args"]["_contractor"],
            "arbiter": log["args"]["_arbiter"],
            "termsHash": log["args"]["_termsHash"]
        }

    @staticmethod
    def SendFunds(log):
        return {
            "who": log["args"]["who"],
            "howMuch": log["args"]["howMuch"]
        }

    @staticmethod
    def ContractorPaid(log):
        return {
            "contractor": log["args"]["contractor"],
            "amount": log["args"]["amount"]
        }

    @staticmethod
    def ContributorWithdrawn(log):
        return {
            "contributor": log["args"]["contributor"],
            "amount": log["args"]["amount"]
        }

    @staticmethod
    def ProjectDisputed(log):
        return {
            "by": log["args"]["by"]
        }

    @staticmethod
    def ProjectClosed(log):
        return {
            "by": log["args"]["by"]
        }

    @staticmethod
    def ContractSigned(log):
        return {
            "contractor": log["args"]["contractor"]
        }

    @staticmethod
    def ArbitrationDecision(log):
        return {
            "arbiter": log["args"]["arbiter"],
            "percent": log["args"]["percent"],
            "rulingHash": log["args"]["rulingHash"]
        }
