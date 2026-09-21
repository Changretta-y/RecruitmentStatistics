pipeline {
    agent any

    options {
        timestamps()
        disableConcurrentBuilds()
        skipDefaultCheckout(true)
    }

    triggers {
        pollSCM('H/5 * * * *')
    }

    environment {
        COMPOSE_PROJECT_NAME = 'job'
        DEPLOY_ENV_FILE = '/opt/deploy/job/.env'
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Validate build tools') {
            steps {
                sh 'docker version'
                sh 'docker compose version'
                sh 'test -f docker-compose.yml'
                sh 'test -f backend/Dockerfile'
                sh 'test -f frontend/Dockerfile'
            }
        }

        stage('Build images') {
            steps {
                sh 'docker compose --env-file "$DEPLOY_ENV_FILE" build backend frontend'
            }
        }

        stage('Deploy production') {
            when {
                branch 'release'
            }
            steps {
                sh '''
                    docker compose --env-file "$DEPLOY_ENV_FILE" up -d --remove-orphans
                    docker compose --env-file "$DEPLOY_ENV_FILE" ps
                '''
            }
        }

        stage('Smoke test') {
            when {
                branch 'release'
            }
            steps {
                sh '''
                    docker run --rm --network host curlimages/curl:8.10.1 \
                      -fsS http://127.0.0.1:5173/ >/dev/null
                    docker run --rm --network host curlimages/curl:8.10.1 \
                      -fsS -H 'Host: 115.190.240.84' \
                      http://127.0.0.1:5173/api/v1/health/
                '''
            }
        }
    }

    post {
        always {
            sh 'docker compose --env-file "$DEPLOY_ENV_FILE" ps || true'
        }
    }
}
