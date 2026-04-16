pipeline {
    agent any

    parameters {
        // Manual version control ke liye
        string(name: 'IMAGE_TAG', defaultValue: 'v1', description: 'Enter the version to deploy (e.g., v1, v2, v3)')
    }

    environment {
        // Aapka DockerHub Username
        DOCKER_USER = "devopsghazali" 
        APP_NAME = "websites_finding"
        // GitOps Repo details
        GITOPS_REPO = "github.com/devopsghazali/gitops_web_find.git"
    }

    stages {
        stage('Cleanup Workspace') {
            steps {
                cleanWs()
            }
        }

        stage('Checkout Source') {
            steps {
                // Main code repo uthana
                checkout scm
            }
        }

        stage('Build & Push Docker Image') {
            steps {
                script {
                    // Yahan hum aapka manual tag 'v1/v2' aur 'latest' dono push karenge
                    def fullImageName = "${DOCKER_USER}/${APP_NAME}:${params.IMAGE_TAG}"
                    
                    sh "docker build -t ${fullImageName} -t ${DOCKER_USER}/${APP_NAME}:latest ."
                    
                    // Jenkins Credentials se DockerHub login
                    withCredentials([usernamePassword(credentialsId: 'dockerhub-creda', passwordVariable: 'DOCKER_PASS', usernameVariable: 'DOCKER_USER_ID')]) {
                        sh "echo $DOCKER_PASS | docker login -u $DOCKER_USER_ID --password-stdin"
                        sh "docker push ${fullImageName}"
                        sh "docker push ${DOCKER_USER}/${APP_NAME}:latest"
                    }
                }
            }
        }

        stage('Update GitOps Manifest') {
            steps {
                script {
                    // 1. GitOps Repo ko clone karna
                    sh "git clone https://${GITOPS_REPO} temp_gitops"
                    
                    dir('temp_gitops') {
                        // 2. 'sed' command se deployment.yaml mein image tag badalna
                        // Yeh command purane kisi bhi version ko naye manual version se replace kar degi
                        sh "sed -i 's|image: ${DOCKER_USER}/${APP_NAME}:.*|image: ${DOCKER_USER}/${APP_NAME}:${params.IMAGE_TAG}|' deployment.yaml"
                        
                        // 3. GitHub par wapas push karna (using your Secret Token)
                        withCredentials([string(credentialsId: 'github-token-secret', variable: 'G_TOKEN')]) {
                            sh "git config user.email 'jenkins@devopsghazali.com'"
                            sh "git config user.name 'Jenkins CI Bot'"
                            sh "git add deployment.yaml"
                            sh "git commit -m 'Release ${params.IMAGE_TAG}: Image updated by Jenkins'"
                            sh "git push https://${G_TOKEN}@${GITOPS_REPO} main"
                        }
                    }
                }
            }
        }
    }

    post {
        always {
            echo "Pipeline finished executing."
        }
        success {
            echo "Image ${params.IMAGE_TAG} is now live in GitOps repo!"
        }
    }
}
