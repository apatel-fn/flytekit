import flyteidl.admin.launch_plan_pb2 as _launch_plan_pb2
import flyteidl.admin.task_pb2 as _task_pb2
import flyteidl.admin.workflow_pb2 as _workflow_pb2
import flyteidl.core.tasks_pb2 as _core_task_pb2
import pytest
from flyteidl.core import identifier_pb2 as _identifier_pb2
from flyteidl.core import workflow_pb2 as _core_workflow_pb2

from flytekit.clis import helpers
from flytekit.clis.helpers import _hydrate_identifier, _hydrate_workflow_template, hydrate_registration_parameters
from flytekit.models import literals, types
from flytekit.models.interface import Parameter, ParameterMap, Variable


def test_parse_args_into_dict():
    sample_args1 = (u"input_b=mystr", u"input_c=18")
    sample_args2 = ("input_a=mystr===d",)
    sample_args3 = ()
    output = helpers.parse_args_into_dict(sample_args1)
    assert output["input_b"] == "mystr"
    assert output["input_c"] == "18"

    output = helpers.parse_args_into_dict(sample_args2)
    assert output["input_a"] == "mystr===d"

    output = helpers.parse_args_into_dict(sample_args3)
    assert output == {}


def test_construct_literal_map_from_variable_map():
    v = Variable(type=types.LiteralType(simple=types.SimpleType.INTEGER), description="some description")
    variable_map = {
        "inputa": v,
    }

    input_txt_dictionary = {"inputa": "15"}

    literal_map = helpers.construct_literal_map_from_variable_map(variable_map, input_txt_dictionary)
    parsed_literal = literal_map.literals["inputa"].value
    ll = literals.Scalar(primitive=literals.Primitive(integer=15))
    assert parsed_literal == ll


def test_construct_literal_map_from_parameter_map():
    v = Variable(type=types.LiteralType(simple=types.SimpleType.INTEGER), description="some description")
    p = Parameter(var=v, required=True)
    pm = ParameterMap(parameters={"inputa": p})

    input_txt_dictionary = {"inputa": "15"}

    literal_map = helpers.construct_literal_map_from_parameter_map(pm, input_txt_dictionary)
    parsed_literal = literal_map.literals["inputa"].value
    ll = literals.Scalar(primitive=literals.Primitive(integer=15))
    assert parsed_literal == ll

    with pytest.raises(Exception):
        helpers.construct_literal_map_from_parameter_map(pm, {})


def test_strtobool():
    assert not helpers.str2bool("False")
    assert not helpers.str2bool("OFF")
    assert not helpers.str2bool("no")
    assert not helpers.str2bool("0")
    assert helpers.str2bool("t")
    assert helpers.str2bool("true")
    assert helpers.str2bool("stuff")


def test_hydrate_identifier():
    identifier = _hydrate_identifier("project", "domain", "12345", _identifier_pb2.Identifier())
    assert identifier.project == "project"
    assert identifier.domain == "domain"
    assert identifier.version == "12345"

    identifier = _hydrate_identifier(
        "project2", "domain2", "abc", _identifier_pb2.Identifier(project="project", domain="domain", version="12345")
    )
    assert identifier.project == "project"
    assert identifier.domain == "domain"
    assert identifier.version == "12345"


def test_hydrate_workflow_template():
    workflow_template = _core_workflow_pb2.WorkflowTemplate()
    workflow_template.nodes.append(
        _core_workflow_pb2.Node(
            id="task_node",
            task_node=_core_workflow_pb2.TaskNode(
                reference_id=_identifier_pb2.Identifier(resource_type=_identifier_pb2.TASK)
            ),
        )
    )
    workflow_template.nodes.append(
        _core_workflow_pb2.Node(
            id="launchplan_ref",
            workflow_node=_core_workflow_pb2.WorkflowNode(
                launchplan_ref=_identifier_pb2.Identifier(
                    resource_type=_identifier_pb2.LAUNCH_PLAN, project="project2",
                )
            ),
        )
    )
    workflow_template.nodes.append(
        _core_workflow_pb2.Node(
            id="sub_workflow_ref",
            workflow_node=_core_workflow_pb2.WorkflowNode(
                sub_workflow_ref=_identifier_pb2.Identifier(
                    resource_type=_identifier_pb2.WORKFLOW, project="project2", domain="domain2",
                )
            ),
        )
    )
    workflow_template.nodes.append(
        _core_workflow_pb2.Node(
            id="unchanged",
            task_node=_core_workflow_pb2.TaskNode(
                reference_id=_identifier_pb2.Identifier(
                    resource_type=_identifier_pb2.TASK, project="project2", domain="domain2", version="abc"
                )
            ),
        )
    )
    hydrated_workflow_template = _hydrate_workflow_template("project", "domain", "12345", workflow_template)
    assert len(hydrated_workflow_template.nodes) == 4
    task_node_identifier = hydrated_workflow_template.nodes[0].task_node.reference_id
    assert task_node_identifier.project == "project"
    assert task_node_identifier.domain == "domain"
    assert task_node_identifier.version == "12345"

    launchplan_ref_identifier = hydrated_workflow_template.nodes[1].workflow_node.launchplan_ref
    assert launchplan_ref_identifier.project == "project2"
    assert launchplan_ref_identifier.domain == "domain"
    assert launchplan_ref_identifier.version == "12345"

    sub_workflow_ref_identifier = hydrated_workflow_template.nodes[2].workflow_node.sub_workflow_ref
    assert sub_workflow_ref_identifier.project == "project2"
    assert sub_workflow_ref_identifier.domain == "domain2"
    assert sub_workflow_ref_identifier.version == "12345"

    unchanged_identifier = hydrated_workflow_template.nodes[3].task_node.reference_id
    assert unchanged_identifier.project == "project2"
    assert unchanged_identifier.domain == "domain2"
    assert unchanged_identifier.version == "abc"


def test_hydrate_registration_parameters__launch_plan_already_set():
    launch_plan = _launch_plan_pb2.LaunchPlanSpec(
        workflow_id=_identifier_pb2.Identifier(
            resource_type=_identifier_pb2.WORKFLOW,
            project="project2",
            domain="domain2",
            name="workflow_name",
            version="abc",
        )
    )
    identifier, entity = hydrate_registration_parameters(
        _identifier_pb2.Identifier(
            resource_type=_identifier_pb2.LAUNCH_PLAN,
            project="project2",
            domain="domain2",
            name="workflow_name",
            version="abc",
        ),
        "project",
        "domain",
        "12345",
        launch_plan,
    )
    assert identifier == _identifier_pb2.Identifier(
        resource_type=_identifier_pb2.LAUNCH_PLAN,
        project="project2",
        domain="domain2",
        name="workflow_name",
        version="abc",
    )
    assert entity.workflow_id == launch_plan.workflow_id


def test_hydrate_registration_parameters__launch_plan_nothing_set():
    launch_plan = _launch_plan_pb2.LaunchPlanSpec(
        workflow_id=_identifier_pb2.Identifier(resource_type=_identifier_pb2.WORKFLOW, name="workflow_name",)
    )
    identifier, entity = hydrate_registration_parameters(
        _identifier_pb2.Identifier(resource_type=_identifier_pb2.LAUNCH_PLAN, name="workflow_name"),
        "project",
        "domain",
        "12345",
        launch_plan,
    )
    assert identifier == _identifier_pb2.Identifier(
        resource_type=_identifier_pb2.LAUNCH_PLAN,
        project="project",
        domain="domain",
        name="workflow_name",
        version="12345",
    )
    assert entity.workflow_id == _identifier_pb2.Identifier(
        resource_type=_identifier_pb2.WORKFLOW,
        project="project",
        domain="domain",
        name="workflow_name",
        version="12345",
    )


def test_hydrate_registration_parameters__task_already_set():
    task = _task_pb2.TaskSpec(
        template=_core_task_pb2.TaskTemplate(
            id=_identifier_pb2.Identifier(
                resource_type=_identifier_pb2.TASK, project="project2", domain="domain2", name="name", version="abc",
            ),
        )
    )
    identifier, entity = hydrate_registration_parameters(task.template.id, "project", "domain", "12345", task)
    assert (
        identifier
        == _identifier_pb2.Identifier(
            resource_type=_identifier_pb2.TASK, project="project2", domain="domain2", name="name", version="abc",
        )
        == entity.template.id
    )


def test_hydrate_registration_parameters__task_nothing_set():
    task = _task_pb2.TaskSpec(
        template=_core_task_pb2.TaskTemplate(
            id=_identifier_pb2.Identifier(resource_type=_identifier_pb2.TASK, name="name",),
        )
    )
    identifier, entity = hydrate_registration_parameters(task.template.id, "project", "domain", "12345", task)
    assert (
        identifier
        == _identifier_pb2.Identifier(
            resource_type=_identifier_pb2.TASK, project="project", domain="domain", name="name", version="12345",
        )
        == entity.template.id
    )


def test_hydrate_registration_parameters__workflow_already_set():
    workflow = _workflow_pb2.WorkflowSpec(
        template=_core_workflow_pb2.WorkflowTemplate(
            id=_identifier_pb2.Identifier(
                resource_type=_identifier_pb2.WORKFLOW,
                project="project2",
                domain="domain2",
                name="name",
                version="abc",
            ),
        )
    )
    identifier, entity = hydrate_registration_parameters(workflow.template.id, "project", "domain", "12345", workflow)
    assert (
        identifier
        == _identifier_pb2.Identifier(
            resource_type=_identifier_pb2.WORKFLOW, project="project2", domain="domain2", name="name", version="abc",
        )
        == entity.template.id
    )


def test_hydrate_registration_parameters__workflow_nothing_set():
    workflow = _workflow_pb2.WorkflowSpec(
        template=_core_workflow_pb2.WorkflowTemplate(
            id=_identifier_pb2.Identifier(resource_type=_identifier_pb2.WORKFLOW, name="name",),
        )
    )
    identifier, entity = hydrate_registration_parameters(workflow.template.id, "project", "domain", "12345", workflow)
    assert (
        identifier
        == _identifier_pb2.Identifier(
            resource_type=_identifier_pb2.WORKFLOW, project="project", domain="domain", name="name", version="12345",
        )
        == entity.template.id
    )
