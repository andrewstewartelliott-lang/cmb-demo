helm lint ./app
helm repo add secrets-store-csi-driver \
  https://kubernetes-sigs.github.io/secrets-store-csi-driver/charts
helm upgrade --install -n kube-system csi-secrets-store \
  secrets-store-csi-driver/secrets-store-csi-driver
helm upgrade --install app ./app \
  --set image.tag="1.0.0" \
  --namespace app \
  --create-namespace
