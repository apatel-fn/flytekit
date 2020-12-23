from dataclasses import dataclass
from typing import TypeVar, Dict, Any, Callable

from google.protobuf.json_format import MessageToDict

from flytekit.annotated.base_task import PythonTask, kwtypes
from flytekit.annotated.context_manager import RegistrationSettings
from flytekit.annotated.interface import Interface
from flytekit.annotated.python_function_task import PythonFunctionTask
from flytekit.annotated.task import TaskPlugins
from flytekit.models import task as _task_model
from flytekit.models.sagemaker import training_job as _training_job_models
from flytekit.types import FlyteFile


@dataclass
class SagemakerTrainingJobConfig(object):
    """
    Configuration for Running Training Jobs on Sagemaker. This config can be used to run either the built-in algorithms
    or custom algorithms.

    Args:
        training_job_resource_config: Configuration for Resources to use during the training
        algorithm_specification: Specification of the algorithm to use
    """
    training_job_resource_config: _training_job_models.TrainingJobResourceConfig
    algorithm_specification: _training_job_models.AlgorithmSpecification


class SagemakerBuiltinAlgorithmsTask(PythonTask):
    """
    Implements an interface that allows execution of a SagemakerBuiltinAlgorithms.
    Refer to `Sagemaker Builtin Algorithms<https://docs.aws.amazon.com/sagemaker/latest/dg/algos.html>`_ for details.
    """

    _SAGEMAKER_TRAINING_JOB_TASK = "sagemaker_training_job_task"

    OUTPUT_TYPE = TypeVar("tar.gz")

    def __init__(self, name: str, metadata: _task_model.TaskMetadata, task_config: SagemakerTrainingJobConfig, *args,
                 **kwargs):
        """
        Args:
            name: name of this specific task. This should be unique within the project. A good strategy is to prefix
                  with the module name
            metadata: Metadata for the task
            task_config: Config to use for the SagemakerBuiltinAlgorithms
        """
        if (task_config is None or
                task_config.algorithm_specification is None or
                task_config.training_job_resource_config is None):
            raise ValueError("TaskConfig, algorithm_specification, training_job_resource_config are required")

        input_type = TypeVar(self._content_type_to_blob_format(task_config.algorithm_specification.input_content_type))

        interface = Interface(
            # TODO change train and validation to be FlyteDirectory when available
            inputs=kwtypes(static_hyperparameters=dict, train=FlyteFile[input_type], validation=FlyteFile[input_type]),
            outputs=kwtypes(model=FlyteFile[self.OUTPUT_TYPE]),
        )
        super().__init__(self._SAGEMAKER_TRAINING_JOB_TASK, name, interface, metadata, *args, **kwargs)
        self._task_config = task_config

    @property
    def task_config(self) -> SagemakerTrainingJobConfig:
        return self._task_config

    def get_custom(self, settings: RegistrationSettings) -> Dict[str, Any]:
        training_job = _training_job_models.TrainingJob(
            algorithm_specification=self._task_config.algorithm_specification,
            training_job_resource_config=self._task_config.training_job_resource_config,
        )
        return MessageToDict(training_job.to_flyte_idl())

    def execute(self, **kwargs) -> Any:
        raise NotImplementedError("Cannot execute Sagemaker Builtin Algorithms locally, for local testing, please mock!")

    @classmethod
    def _content_type_to_blob_format(cls, content_type: int) -> str:
        """
        TODO Convert InputContentType to Enum and others
        """
        if content_type == _training_job_models.InputContentType.TEXT_CSV:
            return "csv"
        else:
            raise ValueError("Unsupported InputContentType: {}".format(content_type))


class SagemakerCustomTrainingTask(PythonFunctionTask[SagemakerTrainingJobConfig]):
    """
    Allows a custom training algorithm to be executed on Amazon Sagemaker. For this to work, make sure your container
    is built according to Flyte plugin documentation (TODO point the link here)
    """
    _SAGEMAKER_CUSTOM_TRAINING_JOB_TASK = "sagemaker_custom_training_job_task"

    def __init__(self, task_config: SagemakerTrainingJobConfig, task_function: Callable,
                 metadata: _task_model.TaskMetadata, *args, **kwargs):
        super().__init__(task_config, task_function, metadata,
                         task_type=self._SAGEMAKER_CUSTOM_TRAINING_JOB_TASK, *args, **kwargs)

    def get_custom(self, settings: RegistrationSettings) -> Dict[str, Any]:
        training_job = _training_job_models.TrainingJob(
            algorithm_specification=self.task_config.algorithm_specification,
            training_job_resource_config=self.task_config.training_job_resource_config,
        )
        return MessageToDict(training_job.to_flyte_idl())


# Register the Tensorflow Plugin into the flytekit core plugin system
TaskPlugins.register_pythontask_plugin(SagemakerTrainingJobConfig, SagemakerCustomTrainingTask)