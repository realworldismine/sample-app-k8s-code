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
                        user = docker.build "onikaze/sample-app-k8s-user"
                    }
                }
                dir('./post') {
                    script {
                        post = docker.build "onikaze/sample-app-k8s-post"
                    }
                }
                dir('./notification') {
                    script {
                        notification = docker.build "onikaze/sample-app-k8s-notification"
                    }
                }
            }
        }

        stage('Push image') {
            steps {
                script {
                    docker.withRegistry('https://registry.hub.docker.com', 'dockerhub') {                
                        user.push("${env.BUILD_NUMBER}")
                        post.push("${env.BUILD_NUMBER}")
                        notification.push("${env.BUILD_NUMBER}")
                        user.push("latest")
                        post.push("latest")
                        notification.push("latest")
                    }
                }
            }
        }
        
        stage('Trigger ManifestUpdate') {
            steps {
                echo "triggering updatemanifestjob"
                build job: 'updatemanifestjob', parameters: [string(name: 'DOCKERTAG', value: env.BUILD_NUMBER)]
            }
        }
    }
}
