# API Reference

Base URL: `https://your-service.onrender.com`

All POST/PUT endpoints accept `Content-Type: application/json`.

All responses return JSON with a `success` boolean field.

---

## Notes

### List Notes

```
GET /api/notes
GET /api/notes?search=keyword
```

**Response (200):**
```json
[
  {
    "id": 1,
    "title": "My Note",
    "content": "Note content here",
    "created_at": "2026-08-25 10:30:00",
    "updated_at": "2026-08-25 10:30:00"
  }
]
```

### Get Single Note

```
GET /api/notes/<id>
```

**Response (200):**
```json
{
  "success": true,
  "note": {
    "id": 1,
    "title": "My Note",
    "content": "Note content here",
    "created_at": "2026-08-25 10:30:00",
    "updated_at": "2026-08-25 10:30:00"
  }
}
```

**Response (404):**
```json
{
  "success": false,
  "message": "Note not found"
}
```

### Create Note

```
POST /api/notes
```

**Request Body:**
```json
{
  "title": "My Note",
  "content": "Note content here"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Note created successfully",
  "note": {
    "id": 1,
    "title": "My Note",
    "content": "Note content here",
    "created_at": "2026-08-25 10:30:00",
    "updated_at": "2026-08-25 10:30:00"
  }
}
```

**Response (400):**
```json
{
  "success": false,
  "message": "Title and content are required"
}
```

### Update Note

```
PUT /api/notes/<id>
```

**Request Body:**
```json
{
  "title": "Updated Title",
  "content": "Updated content"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Note updated successfully",
  "note": {
    "id": 1,
    "title": "Updated Title",
    "content": "Updated content",
    "created_at": "2026-08-25 10:30:00",
    "updated_at": "2026-08-25 11:00:00"
  }
}
```

### Delete Note

```
DELETE /api/notes/<id>
```

**Response (200):**
```json
{
  "success": true,
  "message": "Note deleted successfully"
}
```

**Response (404):**
```json
{
  "success": false,
  "message": "Note not found"
}
```

---

## Waitlist

### Join Waitlist

```
POST /api/waitlist
```

**Request Body:**
```json
{
  "name": "John",
  "email": "john@example.com"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "You're on the waitlist!"
}
```

**Response (409):**
```json
{
  "success": false,
  "message": "You're already on the waitlist"
}
```

---

## Authentication

### Create Username

```
POST /api/create_username
```

**Request Body:**
```json
{
  "username": "johndoe"
}
```

**Response (201):**
```json
{
  "success": true,
  "message": "Username created"
}
```

**Response (409):**
```json
{
  "success": false,
  "message": "Username already taken"
}
```

### Set Password

```
POST /api/create_password
```

**Request Body:**
```json
{
  "username": "johndoe",
  "password": "securepass123"
}
```

**Response (200):**
```json
{
  "success": true,
  "message": "Password set successfully"
}
```

**Note:** Passwords are hashed with SHA-256 before storage.

### Get Username

```
GET /api/get_username?username=johndoe
```

**Response (200):**
```json
{
  "success": true,
  "user": {
    "id": 1,
    "username": "johndoe",
    "created_at": "2026-08-25 10:30:00"
  }
}
```

### Check Password Status

```
GET /api/get_password?username=johndoe
```

**Response (200):**
```json
{
  "success": true,
  "has_password": true
}
```

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad request (missing fields, invalid data) |
| 404 | Resource not found |
| 409 | Conflict (duplicate entry) |
| 500 | Server error |
