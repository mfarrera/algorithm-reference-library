#!/usr/bin/env groovy
// SIP Jenkinsfile (CI/CD pipline)
//
// https://jenkins.io/doc/book/pipeline/jenkinsfile/
//
// Stages section:
// - Setup
// - Build
// - Test
//
// Post section: (https://jenkins.io/doc/book/pipeline/syntax/#post)


node {
    label 'sdp-ci-01'
    stage('Checkout'){
	echo 'Checking out repository'
	checkout([$class: 'GitSCM', branches: [[name: '*/master']], doGenerateSubmoduleConfigurations: false, extensions: [[$class: 'CleanBeforeCheckout'], [$class: 'GitLFSPull']], submoduleCfg: [], userRemoteConfigs: [[credentialsId: '2ca2f96d-f272-46d1-accf-8b64a4a0a48e', url: 'https://github.com/mfarrera/algorithm-reference-library']]])
    }
    stage('Setup') {
	echo "Running ${env.BUILD_ID} on ${env.JENKINS_URL}"
        echo 'Setting up a fresh Python virtual environment...'
	sh '''
	virtualenv -p `which python3` _build
	echo 'Activating virtual environment...'
	source _build/bin/activate
	echo 'Installing requirements'
	pip install -U pip setuptools
	pip install coverage numpy
	pip install virtualenvwrapper
	pip install -r requirements.txt
	echo 'Adding the arl and ffiwrappers path to the virtual environment'
	echo '(equivalent to setting up PYTHONPATH environment variable'
	source virtualenvwrapper.sh
	add2virtualenv "${env.WORKSPACE}"
	add2virtualenv "${env.WORKSPACE}/ffiwrappers/src"
	'''
    }
}

