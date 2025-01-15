from abis import economyAbi
from apps.trustless.project import Project


class Economy:
    def __init__(self, contract):
        self.projects = []
        self.contract = contract

    def add_project(self, project: Project, log):
        try:
            self.projects.append(project)
            project.store()

        except Exception as e:
            print(e)
