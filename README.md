# CMB k8s python api demo
These responses are related to the requirements which were provided to me on behalf of the client, CMB.
Application was developed on kubernetes-in-docker to save money so there may be some extra steps before it can be run in aws.

Application:

The app is generic python with FastAPI overlay running on port 8000.  It currently has the following api endpoints:
/         - root (used by liveness and readiness probes)
/payments - external api which is hit by 3rd party payment service
/batch    - batch api used for large jobs run once a day
/write    - tests db write to external rds instance (not hooked up, cost prohibitive)
/metrics  - app metrics, required for horizontal pod auto-scaling based on requests load

I use external uvicorn to run the application rather than have python run it directly.  This would allow us to change the underlying server without changing the application code.

Secrets Management(not implemented but visible):

DB secrets and connection strings are stored in a secrets-manager store in AWS.  They are consumed by the helm deployment template, by way of secretprovider.yaml.  Secrets are mounted in the deployment and consumed by the python application at deploy time.  Using this method, secrets are mounted directly in the pod and the pod will restart whenever the credentials are rotated.  It requires a controller (aws-external-secrets-provider) to be running to actually pull the secrets object.  This controller should only run with least-priviledge access, it's AWS policy should be restricted and hooked up to the serviceAccount via IRSA.

Docker Image

Image is built and tagged locally and pushed to dockerhub with my account, where it will be consumed by the helm chart.  Current image is 1.0.0.
https://hub.docker.com/repository/docker/andrewstewartelliott/app/general
Images are currently scanned with Trivy (see github workflows).  In the future I would perform automated penetration tests with zap and kubernetes resource orchestrator.

Helm Deployment

This is a custom-built helm chart, stored and run locally, which delivers the following:
deployment  - standard, mounts external-secrets directly, variable replicas
hpa         - used for scaling
ingress     - used to map domain into the cluster (should work natively with external-dns or similar)
service     - expose the services to the cluster

*** Note ***
ingress-gateway is deprecated and should be replaced with gateway-api and httproutes.  It was deprecated at the start of this year and should be replaced.

Scaling (HPA, based on `http_requests_total`)

HPA is configured in helm values file, under autoscaling.  It takes 2 arguments: minReplica and maxReplica.
If we figure 100 requests/second per pod, we will use a minimum of 1 pod and a maximum of 30.  30 replicas will serve 3000 requests/second as stated in the requirements and dynamically change with the load.  We do not need to worry about time of day or manual scaling as pods will expand based on the metrics which are provided by python.
We will still need to implement a prometheus adapter for this cluster, which will expose the metrics to the k8s api and allow hpa to scale based on those metrics.

Delivery

Deployments to the cluster will be performed with Helm via github workflows (see .github/workflows).  Currently there are 2: deploySTAGING and deployPROD.  Both accept the version of application with workflow dispatch but in the future I would automate this to deploy to staging automatically after a good merge with main.
Ideally I would implement ArgoCD or FluxCD to help with faster sync, but neither tool was listed in the job description so I left it out.
Deployments can be run locally with the "helm.sh" script.  Pre-requisite is to have csi-secret-store-drive in order for the secretprovider to work correctly.  Deployments can easily be rolled back in production with the `helm rollback` command.  As this is a deployment and not a statefulset, we can see the complete history of deployments without an external tool.

Monitoring/Observability (not implemented because of time)

How would I know the service is healthy?
readiness and liveness probes in the helm deployment
create synthetic checks via datadog, kuberhealthy or grafana/prom which:
- connect to each endpoint and test response time
- validate data received by endpoints
- run test write to db and test the speed
- monitor read/write latency of DB
- monitor iops of DB
- use an external 3rd party service to test the ingress gateway into the cluster

The end game would be to have a dashboard with all these metrics included so we can guage service health quickly and which is available to business owners.

I would page someone for 503 or 404 application errors, disconnected database, login errors, payment processing errors and more than 30 pods running at one time (or some kind of spend metric).

I would not page someone for increased latency (either app or db writes), moderate volume increase, user-related errors or an increase in generic monitoring logs.  Perhaps not a flapping service as this usually indicates an incorrectly-set monitor threshold.
Ideally we would classify issues from P1 -> P5 and have written procedures for each classification.

end of explanation, start of normal readme.

# Payments API

A FastAPI service that listens on port `8000`, provides payment and batch example endpoints, and exposes Prometheus metrics. The published image is [`andrewstewartelliott/app`](https://hub.docker.com/repository/docker/andrewstewartelliott/app/general).

## API

| Method | Path | Behavior |
| --- | --- | --- |
| `GET` | `/` | Returns `{"message":"hello"}` |
| `GET` | `/payments` | Returns `{"message":"payment api"}` |
| `GET` | `/batch` | Returns `{"message":"batch api"}` |
| `GET` | `/metrics` | Prometheus metrics, including `http_requests_total` |

Requests to `/metrics` are excluded from `http_requests_total`.

`POST /write` is not currently implemented. A PostgreSQL write example remains commented out in `main.py`; although the psycopg driver is installed, database secret mounting and connection setup are not active.

## Run locally

Requires Python 3.12 or newer.

```sh
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

The API is available at `http://localhost:8000`. `./run.sh` starts the same server after dependencies are installed.

## Docker

Build and publish version `1.0.0` (requires Docker and permission to push to the Docker Hub repository):

```sh
./dockerbuildandpush.sh
```

Run the published image locally:

```sh
docker run --rm -p 8000:8000 andrewstewartelliott/app:1.0.0
```

## Kubernetes and Helm

The chart is in `app/`. It uses image `andrewstewartelliott/app:1.0.0`, exposes a ClusterIP service on port `8000`, and enables an ingress by default. A Kubernetes cluster and Helm are required.

```sh
helm lint ./app
helm upgrade --install app ./app \
	--set image.tag="1.0.0" \
	--namespace app \
	--create-namespace
```

`./helm.sh` also installs the Secrets Store CSI Driver chart before deploying the app. The chart's `SecretProviderClass` is an AWS example placeholder; it requires a working CSI provider configuration to use. The Deployment currently does not mount these secrets into the container.

Autoscaling is enabled by default for 1 to 30 replicas and expects the custom metric `http_requests_per_second`, which requires a compatible metrics adapter. Adjust chart settings in `app/values.yaml` as needed.

To access the service through Kubernetes port forwarding:

```sh
kubectl port-forward --namespace app service/app 8000:8000
```

Then visit `http://localhost:8000`. Remove the release with `helm uninstall app --namespace app`.

For a local KinD ingress setup, `./kind-ingress.sh` installs and runs `cloud-provider-kind`; it requires Go and `sudo`. After the ingress controller and chart are running, inspect the address with `kubectl get ingress --namespace app`.

## GitHub Actions

On each push, `.github/workflows/tests.yml` runs the Python linter and scans the published `andrewstewartelliott/app:1.0.0` image with Trivy, failing for HIGH or CRITICAL OS or library vulnerabilities.

`.github/workflows/deploySTAGING.yml` and `.github/workflows/deployPROD.yml` are manually dispatched and accept an `app_version` image tag. Both currently deploy the Helm release `app` to namespace `app`; the PROD workflow is not isolated from staging.

## unit tests
```
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
```