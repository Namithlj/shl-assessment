# Deploy to Render — checklist

1. Ensure repository is pushed to GitHub (branch: `main`).
2. In Render dashboard, create a new **Web Service** and connect your GitHub repo.
   - Render will detect `render.yaml` and/or the `Dockerfile`.

3. Set environment variables (Service > Environment):
   - `HF_TOKEN` = <your Hugging Face token> (required to speed model downloads)
   - `PYTHONUNBUFFERED=1` (optional, improves logs)

4. Build & Start configuration (if not using `render.yaml`):
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn api.server:app --bind 0.0.0.0:$PORT --workers 2`

5. Artifacts & storage:
   - If your index and embeddings are large, either:
     - Precompute `data/embeddings.npy`, `data/nn_model.joblib`, `data/metadata.json` and commit (not recommended for large files), or
     - Persist them to an external store (S3) and load at startup (modify `load_resources`).

6. Health & tests:
   - After deploy open `https://<your-service-url>/` to see the frontend.
   - POST to `/recommend` or use the UI to verify recommendations.

7. Troubleshooting:
   - If you see HF rate-limit warnings, verify `HF_TOKEN` is set.
   - If scikit-learn Unpickle warnings appear, rebuild the index in the same runtime and commit the artifacts built with the same sklearn version.

8. Optional: Use the `Dockerfile` to build locally and test:
   ```bash
   docker build -t shl-assessment .
   docker run -e PORT=8181 -p 8181:8181 shl-assessment
   ```

---
If you want, I can push these changes to Git and open a PR, or proceed to prepare a Docker image and a sample Render deployment draft. Reply `push` to push now.
