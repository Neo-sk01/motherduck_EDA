from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_teamcity_dsl_migrates_all_ci_cd_targets() -> None:
    settings = read(".teamcity/settings.kts")

    assert 'version = "2025.11"' in settings
    assert "object CI : BuildType" in settings
    assert "object DeployPipelineImage : BuildType" in settings
    assert "object DeployFunction : BuildType" in settings
    assert "object DeployDashboard : BuildType" in settings
    assert "object DeployAll : BuildType" in settings
    assert "BuildTypeSettings.Type.DEPLOYMENT" in settings
    assert "ci/teamcity/python-tests.sh" in settings
    assert "ci/teamcity/dashboard-tests.sh" in settings
    assert "ci/teamcity/docker-build.sh" in settings
    assert "ci/teamcity/deploy-pipeline-image.sh" in settings
    assert "ci/teamcity/deploy-function.sh" in settings
    assert "ci/teamcity/deploy-dashboard.sh" in settings
    assert "python-runner" not in settings.lower()
    assert "teamcity-messages" not in settings.lower()


def test_teamcity_scripts_use_venv_and_secure_azure_parameters() -> None:
    python_tests = read("ci/teamcity/python-tests.sh")
    lib = read("ci/teamcity/lib.sh")
    deploy_pipeline = read("ci/teamcity/deploy-pipeline-image.sh")
    deploy_function = read("ci/teamcity/deploy-function.sh")
    deploy_dashboard = read("ci/teamcity/deploy-dashboard.sh")

    assert "python3 -m venv" in python_tests
    assert 'pip install -e ".[dev]"' in python_tests
    assert "pytest functions/tests" in python_tests
    assert "docker run --rm" in lib
    assert "mcr.microsoft.com/azure-cli" in lib

    for script in (deploy_pipeline, deploy_function):
        assert "AZURE_CLIENT_ID" in script
        assert "AZURE_CLIENT_SECRET" in script
        assert "AZURE_TENANT_ID" in script
        assert "AZURE_SUBSCRIPTION_ID" in script
        assert "azure_cli" in script

    assert "docker login" in deploy_pipeline
    assert "az containerapp job update" in deploy_pipeline
    assert "az storage blob upload" in deploy_function
    assert "WEBSITE_RUN_FROM_PACKAGE" in deploy_function
    assert "az resource invoke-action" in deploy_function
    assert "export FUNCTION_RELEASE_CONTAINER" in deploy_function
    assert "@azure/static-web-apps-cli" in deploy_dashboard
    assert "SWA_DEPLOYMENT_TOKEN" in deploy_dashboard


def test_github_actions_are_manual_fallbacks_only() -> None:
    for workflow in (
        ".github/workflows/pipeline-image.yml",
        ".github/workflows/function.yml",
        ".github/workflows/dashboard.yml",
    ):
        contents = read(workflow)
        assert "workflow_dispatch:" in contents
        assert "\n  push:" not in contents
