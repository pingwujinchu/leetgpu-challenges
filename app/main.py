import os
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.challenge_loader import discover_challenges, load_challenge_instance, read_challenge_html, get_challenge_name
from app.gpu_utils import gpu_summary

app = FastAPI(title="LeetGPU Online Tester")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    infos = discover_challenges()
    gpus = gpu_summary()
    return templates.TemplateResponse("index.html", {"request": request, "challenges": infos, "gpus": gpus})


@app.get("/challenge/{difficulty}/{folder}", response_class=HTMLResponse)
def challenge_detail(difficulty: str, folder: str, request: Request):
    slug = f"{difficulty}/{folder}"
    matches = [c for c in discover_challenges() if c.slug == slug]
    if not matches:
        raise HTTPException(status_code=404, detail="Challenge not found")
    info = matches[0]

    instance = load_challenge_instance(info)
    html = read_challenge_html(info)
    name = get_challenge_name(instance) or info.folder_name
    gpus = gpu_summary()

    return templates.TemplateResponse("challenge.html", {
        "request": request,
        "challenge": info,
        "challenge_name": name,
        "html": html,
        "gpus": gpus,
    })


@app.post("/challenge/{difficulty}/{folder}/run", response_class=HTMLResponse)
def run_reference(difficulty: str, folder: str, request: Request, gpu: int = Form(None)):
    slug = f"{difficulty}/{folder}"
    matches = [c for c in discover_challenges() if c.slug == slug]
    if not matches:
        raise HTTPException(status_code=404, detail="Challenge not found")
    info = matches[0]

    instance = load_challenge_instance(info)

    # Use the example test for demo purposes
    try:
        # If a GPU index was provided and CUDA is available, switch device
        try:
            import torch
            if gpu is not None and torch.cuda.is_available():
                torch.cuda.set_device(int(gpu))
        except Exception:
            # Non-fatal; proceed and let downstream errors surface if any
            pass

        test = instance.generate_example_test()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate test: {e}")

    # Run the reference
    try:
        # Build args preserving order by reference_impl signature
        from app.challenge_loader import get_reference_signature_params
        names, _ = get_reference_signature_params(instance)
        args = [test[name] for name in names if name in test]
        instance.reference_impl(*args)
        result_summary = "Reference run completed successfully."
    except Exception as e:
        result_summary = f"Error during reference run: {e}"

    # Show back the detail page with a banner
    html = read_challenge_html(info)
    name = getattr(instance, "name", info.folder_name)
    gpus = gpu_summary()

    return templates.TemplateResponse("challenge.html", {
        "request": request,
        "challenge": info,
        "challenge_name": name,
        "html": html,
        "gpus": gpus,
        "result_summary": result_summary,
    })
