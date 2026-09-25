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
        BACKUP_DIR = '/root/backups'
    }

    stages {
        stage('Validate release source') {
            steps {
                script {
                    def checkoutInfo = checkout scm
                    def sourceBranch = env.BRANCH_NAME ?: env.GIT_BRANCH ?: env.GIT_LOCAL_BRANCH ?: checkoutInfo.GIT_BRANCH
                    if (sourceBranch != null) {
                        sourceBranch = sourceBranch
                            .replaceFirst(/^refs\/remotes\/origin\//, '')
                            .replaceFirst(/^refs\/heads\//, '')
                            .replaceFirst(/^origin\//, '')
                            .replaceFirst(/^\*\//, '')
                    }
                    if (sourceBranch != 'release') {
                        error("Production deployment is restricted to the release branch (resolved source: ${sourceBranch ?: 'unknown'}).")
                    }
                }
            }
        }

        stage('Validate build tools') {
            steps {
                sh 'docker version'
                sh 'docker compose version'
                sh 'test -f docker-compose.yml'
                sh 'test -f backend/Dockerfile'
                sh 'test -f frontend/Dockerfile'
                sh 'test -r "$DEPLOY_ENV_FILE"'
            }
        }

        stage('Build release images') {
            steps {
                sh 'docker compose --env-file "$DEPLOY_ENV_FILE" build backend frontend'
            }
        }

        stage('Backup production database') {
            steps {
                sh '''
                    set -eu
                    docker compose --env-file "$DEPLOY_ENV_FILE" up -d db
                    backup_name="job-$(date -u +%Y%m%dT%H%M%SZ).dump"
                    backup_tmp=$(mktemp)
                    trap 'rm -f "$backup_tmp"' EXIT
                    docker compose --env-file "$DEPLOY_ENV_FILE" exec -T db \
                      sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "$backup_tmp"
                    test -s "$backup_tmp"
                    docker run --rm -i -v "$BACKUP_DIR:/backup" alpine:3.20 \
                      sh -c 'set -eu; chmod 700 /backup; umask 077; cat > "/backup/$1"; chmod 600 "/backup/$1"; test -s "/backup/$1"' \
                      sh "$backup_name" < "$backup_tmp"
                    echo "Database backup created at $BACKUP_DIR/$backup_name with root-only permissions."
                '''
            }
        }

        stage('Deploy production') {
            steps {
                sh '''
                    set -eu
                    has_value() {
                      awk -F= -v key="$1" '
                        $1 == key {
                          value = substr($0, index($0, "=") + 1)
                          gsub(/^[[:space:]]+|[[:space:]]+$/, "", value)
                          if (value != "" && value != "\042\042" && value != "\047\047") found = 1
                        }
                        END { exit !found }
                      ' "$DEPLOY_ENV_FILE"
                    }
                    emails_enabled=false
                    if grep -Eq '^[[:space:]]*ENABLE_DAILY_EMAILS[[:space:]]*=[[:space:]]*"?true"?[[:space:]]*(#.*)?$' "$DEPLOY_ENV_FILE"; then
                      for key in EMAIL_HOST EMAIL_PORT EMAIL_HOST_USER EMAIL_HOST_PASSWORD DEFAULT_FROM_EMAIL; do
                        if ! has_value "$key"; then
                          echo "ENABLE_DAILY_EMAILS=true requires non-empty $key; refusing deployment." >&2
                          exit 1
                        fi
                      done
                      emails_enabled=true
                    fi

                    if [ "$emails_enabled" = true ]; then
                      docker compose --env-file "$DEPLOY_ENV_FILE" --profile daily-email up -d --remove-orphans
                      echo 'Daily email scheduler enabled.'
                    else
                      docker compose --env-file "$DEPLOY_ENV_FILE" --profile daily-email stop scheduler || true
                      docker compose --env-file "$DEPLOY_ENV_FILE" --profile daily-email rm -f scheduler || true
                      docker compose --env-file "$DEPLOY_ENV_FILE" up -d --remove-orphans
                      echo 'Daily email scheduler disabled (SMTP is not fully configured or ENABLE_DAILY_EMAILS is not true).'
                    fi
                    docker compose --env-file "$DEPLOY_ENV_FILE" ps
                '''
            }
        }

        stage('Smoke test') {
            steps {
                sh '''
                    set -eu
                    docker run --rm --network host curlimages/curl:8.10.1 \
                      -fsS http://127.0.0.1:5173/ >/dev/null
                    docker run --rm --network host curlimages/curl:8.10.1 \
                      -fsS http://127.0.0.1:5173/calendar >/dev/null
                    docker run --rm --network host curlimages/curl:8.10.1 \
                      -fsS -H 'Host: 115.190.240.84' \
                      http://127.0.0.1:5173/api/v1/health/ >/dev/null
                    calendar_status=$(docker run --rm --network host curlimages/curl:8.10.1 \
                      -sS -o /dev/null -w '%{http_code}' \
                      -H 'Host: 115.190.240.84' \
                      'http://127.0.0.1:5173/api/v1/calendar/events/?start=2026-09-25&end=2026-09-26')
                    case "$calendar_status" in
                      200|401) echo "Calendar API reachable (HTTP $calendar_status)." ;;
                      *) echo "Calendar API smoke failed (HTTP $calendar_status)."; exit 1 ;;
                    esac
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
