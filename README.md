mkdir -p keys
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem

# .gitignore
keys/

chmod 600 keys/private.pem

Em produção, o ideal é:

Armazenar as chaves no Vault (ex: AWS Secrets Manager, HashiCorp Vault, etc.),
ou

Montar as chaves como volumes secretos no container (via Docker/Kubernetes).