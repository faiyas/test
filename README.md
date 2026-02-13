# Camera Demo Backend Instructions

This folder contains a minimal Django backend to test the `CameraComponent`.

## Prerequisites
- Python installed
- Django installed (`pip install django`)
- `django-cors-headers` installed (`pip install django-cors-headers`)

## Setup & Run

1.  **Navigate to the backend directory**:
    ```bash
    cd "d:\campus connection\camera access\camera_demo_backend"
    ```

2.  **Install dependencies** (if not already installed):
    ```bash
    pip install django django-cors-headers
    ```

3.  **Run migrations**:
    ```bash
    python manage.py migrate
    ```

4.  **Start the server**:
    ```bash
    python manage.py runserver 8000
    ```

## API Endpoints

The backend provides the following endpoints to mock your existing API:

-   **Get Camera Status**: `GET http://localhost:8000/api/test-candidate-camera/<id>/`
    -   Returns: `[{ "is_camera_on": true }]`
-   **Upload Screenshot**: `POST http://localhost:8000/api/add-camera-screenshots/<id>/`
    -   Accepts `multipart/form-data` with `screenshots` file field.
    -   Saves images to `screenshots/` directory in the backend folder.

## Frontend Integration

To use this backend with your `CameraComponent`, you need to ensure your `api/endpoints.js` (or wherever your API calls are defined) points to these URLs.

Example `endpoints.js` modification:

```javascript
/* eslint-disable no-undef */
export const getTestcandidateCameraApi = (id) => 
  fetch(`http://localhost:8000/api/test-candidate-camera/${id}/`).then(res => res.json());

export const addCameraScreenshots_API = (id, formData) =>
  fetch(`http://localhost:8000/api/add-camera-screenshots/${id}/`, {
    method: 'POST',
    body: formData
  }).then(res => res.json());
```
