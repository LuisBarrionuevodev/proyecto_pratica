# Dominio Usuarios (Auth + Perfil + Recuperacion)

## Endpoints

- `POST /api/auth/login`
- `POST /api/auth/password-reset/request`
- `POST /api/auth/password-reset/confirm`
- `GET /api/profile/me`
- `PATCH /api/profile/me`
- `POST /api/profile/change-password`
- `GET /api/admin/users`
- `POST /api/admin/users`
- `PUT /api/admin/users/<id>`
- `DELETE /api/admin/users/<id>`

## Ejemplos curl

```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"admin"}'
```

```bash
curl -X POST http://localhost:5000/api/auth/password-reset/request \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@local"}'
```

```bash
curl -X POST http://localhost:5000/api/auth/password-reset/confirm \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@local","code":"123456","new_password":"nueva123","new_password2":"nueva123"}'
```

```bash
curl -X GET http://localhost:5000/api/profile/me \
  -H "Authorization: Bearer <TOKEN>"
```

```bash
curl -X PATCH http://localhost:5000/api/profile/me \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"nickname":"Pablo","avatar_key":"avatar2"}'
```

```bash
curl -X POST http://localhost:5000/api/profile/change-password \
  -H "Authorization: Bearer <TOKEN>" \
  -H "Content-Type: application/json" \
  -d '{"current_password":"admin","new_password":"admin123","new_password2":"admin123"}'
```

```bash
curl -X GET http://localhost:5000/api/admin/users \
  -H "Authorization: Bearer <TOKEN_ADMIN>"
```

```bash
curl -X POST http://localhost:5000/api/admin/users \
  -H "Authorization: Bearer <TOKEN_ADMIN>" \
  -H "Content-Type: application/json" \
  -d '{"username":"nuevo","email":"nuevo@local","password":"secreto123","role":"usuario"}'
```

```bash
curl -X PUT http://localhost:5000/api/admin/users/2 \
  -H "Authorization: Bearer <TOKEN_ADMIN>" \
  -H "Content-Type: application/json" \
  -d '{"role":"admin","is_active":true}'
```

```bash
curl -X DELETE http://localhost:5000/api/admin/users/2 \
  -H "Authorization: Bearer <TOKEN_ADMIN>"
```

