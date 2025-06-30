Run with
```bash
docker compose down && docker compose up -w --build
```

The compose file provides a list of post start commands to run the migrations and populate the db with some initial data.


Inspect and review at:
  http://localhost:8009/graphql/
```graphql
query allUsers {
  users {
    id
    username
    plan
  }
}
```

review traces at:
  - http://localhost:16689/
  - http://localhost:8009/_kolo/


the DB is exposed at localhost:5439

