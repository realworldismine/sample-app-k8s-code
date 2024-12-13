pipeline {
    agent any

    triggers {
        githubPush()
    }
	
    stages {
        stage('Clone repository') {
            checkout scm
        }

        stage('Build image') {
            steps {
                dir('./user') {
                    sh 'sudo docker build -t onikaze/sample-app-k8s-user:latest .'
                }
                dir('./post') {
                    sh 'sudo docker build -t onikaze/sample-app-k8s-post:latest .'
                }
                dir('./notification') {
                    sh 'sudo docker build -t onikaze/sample-app-k8s-notification:latest .'
                }
            }
        }

        stage('Push image') {
            steps {
                docker.withRegistry('https://registry.hub.docker.com', 'dockerhub') {                
                    user.push("latest")
                    post.push("latest")
                    notification.push("latest")
                    // user.push("${env.BUILD_NUMBER}")
                    // post.push("${env.BUILD_NUMBER}")
                    // notification.push("${env.BUILD_NUMBER}")
                }
            }
        }
        
        stage('Trigger ManifestUpdate') {
            steps {
                echo "triggering updatemanifestjob"
                build job: 'updatemanifest', parameters: [string(name: 'DOCKERTAG', value: env.BUILD_NUMBER)]
            }
        }
    }
}
