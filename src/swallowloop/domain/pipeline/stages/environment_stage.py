"""环境准备阶段"""

from ..stage import Stage
from ..tasks.environment_create_workspace_task import EnvironmentCreateWorkspaceTask
from ..tasks.environment_clone_repo_task import EnvironmentCloneRepoTask
from ..tasks.environment_switch_branch_task import EnvironmentSwitchBranchTask
from ..tasks.environment_prepare_env_task import EnvironmentPrepareEnvTask


class EnvironmentStage(Stage):
    """环境准备阶段"""

    def __init__(self):
        super().__init__(name="environment")
        self.tasks = [
            EnvironmentCreateWorkspaceTask(),
            EnvironmentCloneRepoTask(),
            EnvironmentSwitchBranchTask(),
            EnvironmentPrepareEnvTask(),
        ]
