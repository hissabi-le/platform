# infra/terraform/outputs.tf

output "api_ip" {
  description = "public IP of the API droplet"
  value       = digitalocean_droplet.api.ipv4_address
}

output "worker_ip" {
  description = "public IP of the worker droplet"
  value       = digitalocean_droplet.worker.ipv4_address
}

output "db_uri" {
  description = "connection URI for managed Postgres"
  value       = digitalocean_database_cluster.postgres.uri
  sensitive = true
}

output "redis_uri" {
  description = "connection URI for managed Redis"
  value       = digitalocean_database_cluster.redis.uri
  sensitive = true
}

output "spaces_endpoint" {
  description = "endpoint URL for DO Spaces bucket"
  value       = digitalocean_spaces_bucket.uploads.endpoint
}
