pipeline {
    agent any

    triggers {
        githubPush()
    }
	
    stages {
        stage('Build image') {
            steps {
                dir('./user') {
                    script {
                        user = docker.build "onikaze/sample-app-k8s-user:latest"
                    }
                }
                dir('./post') {
                    script {
                        post = docker.build "onikaze/sample-app-k8s-post:latest"
                    }
                }
                dir('./notification') {
                    script {
                        notification = docker.build "onikaze/sample-app-k8s-notification:latest"
                    }
                }
            }
        }

        stage('Push image') {
            steps {
                script {
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
        }
        
        stage('Trigger ManifestUpdate') {
            steps {
                echo "triggering updatemanifestjob"
                build job: 'updatemanifest', parameters: [string(name: 'DOCKERTAG', value: env.BUILD_NUMBER)]
            }
        }
    }
}
