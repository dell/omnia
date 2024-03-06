pipeline {
    agent any
 
    stages {
        stage('Checkout') {
            steps {
                git 'https://github.com/dell/omnia'
            }
        }
        stage('Lint YAML files') {
            steps {
                script {
                    sh 'find . -type f -name "*.yml" -exec ansible-lint {} + || true'
                }
            }
        }
        stage('Send Email') {
            steps {
                emailext (
                    subject: 'Ansible Lint Report',
                    body: 'Please find attached ansible-lint report.',
                    attachLog: true,
                    to: 'soumya.trivedi@dell.com'
                )
            }
        }
    }
}
