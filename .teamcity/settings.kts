import jetbrains.buildServer.configs.kotlin.*
import jetbrains.buildServer.configs.kotlin.BuildType
import jetbrains.buildServer.configs.kotlin.BuildTypeSettings
import jetbrains.buildServer.configs.kotlin.DslContext
import jetbrains.buildServer.configs.kotlin.buildFeatures.perfmon
import jetbrains.buildServer.configs.kotlin.buildSteps.script
import jetbrains.buildServer.configs.kotlin.triggers.vcs

version = "2025.11"

project {
    description = "Versioned TeamCity CI/CD for NeoLore Queue Analytics."

    buildType(CI)
    buildType(DeployPipelineImage)
    buildType(DeployFunction)
    buildType(DeployDashboard)
    buildType(DeployAll)

    buildTypesOrder = arrayListOf(
        CI,
        DeployPipelineImage,
        DeployFunction,
        DeployDashboard,
        DeployAll,
    )
}

object CI : BuildType({
    id("Build")
    name = "CI"
    description = "Runs Python, Function, dashboard, and Docker image checks without deploying."

    vcs {
        root(DslContext.settingsRoot)
    }

    steps {
        script {
            name = "Python tests"
            scriptContent = "bash ci/teamcity/python-tests.sh"
        }
        script {
            name = "Dashboard tests"
            scriptContent = "bash ci/teamcity/dashboard-tests.sh"
        }
        script {
            name = "Docker image build"
            scriptContent = "bash ci/teamcity/docker-build.sh"
        }
    }

    triggers {
        vcs {
            branchFilter = "+:<default>"
        }
    }

    features {
        perfmon {}
    }
})

object DeployPipelineImage : BuildType({
    id("DeployPipelineImage")
    name = "Deploy Pipeline Image"
    type = BuildTypeSettings.Type.DEPLOYMENT
    maxRunningBuilds = 1
    description = "Builds and pushes the pipeline image to ACR, then updates the Azure Container Apps Job."

    vcs {
        root(DslContext.settingsRoot)
    }

    steps {
        script {
            name = "Build, push, and update job"
            scriptContent = "bash ci/teamcity/deploy-pipeline-image.sh"
        }
    }

    triggers {
        vcs {
            branchFilter = "+:<default>"
            triggerRules = """
                +:pipeline/**
                +:pyproject.toml
                +:Dockerfile
                +:.dockerignore
                +:ci/teamcity/**
                +:.teamcity/**
                -:**
            """.trimIndent()
        }
    }

    dependencies {
        snapshot(CI) {}
    }
})

object DeployFunction : BuildType({
    id("DeployFunction")
    name = "Deploy Function"
    type = BuildTypeSettings.Type.DEPLOYMENT
    maxRunningBuilds = 1
    description = "Packages the Azure Function App and points WEBSITE_RUN_FROM_PACKAGE at the new release blob."

    vcs {
        root(DslContext.settingsRoot)
    }

    steps {
        script {
            name = "Package and deploy function"
            scriptContent = "bash ci/teamcity/deploy-function.sh"
        }
    }

    triggers {
        vcs {
            branchFilter = "+:<default>"
            triggerRules = """
                +:functions/**
                +:ci/teamcity/**
                +:.teamcity/**
                -:**
            """.trimIndent()
        }
    }

    dependencies {
        snapshot(CI) {}
    }
})

object DeployDashboard : BuildType({
    id("DeployDashboard")
    name = "Deploy Dashboard"
    type = BuildTypeSettings.Type.DEPLOYMENT
    maxRunningBuilds = 1
    description = "Builds the dashboard and deploys dashboard/dist to Azure Static Web Apps."

    vcs {
        root(DslContext.settingsRoot)
    }

    steps {
        script {
            name = "Build and deploy dashboard"
            scriptContent = "bash ci/teamcity/deploy-dashboard.sh"
        }
    }

    triggers {
        vcs {
            branchFilter = "+:<default>"
            triggerRules = """
                +:dashboard/**
                +:ci/teamcity/**
                +:.teamcity/**
                -:**
            """.trimIndent()
        }
    }

    dependencies {
        snapshot(CI) {}
    }
})

object DeployAll : BuildType({
    id("DeployAll")
    name = "Deploy All"
    type = BuildTypeSettings.Type.DEPLOYMENT
    maxRunningBuilds = 1
    description = "Manual build chain that deploys the pipeline image, Function App, and dashboard at the same revision."

    dependencies {
        snapshot(DeployPipelineImage) {}
        snapshot(DeployFunction) {}
        snapshot(DeployDashboard) {}
    }
})
