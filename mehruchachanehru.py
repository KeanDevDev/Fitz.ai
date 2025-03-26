import os
import time
import shutil
import traceback
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
from transformers import BlipProcessor, BlipForConditionalGeneration
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

# Suppress TensorFlow and Transformers warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

# Initialize FastAPI app
app = FastAPI()

# Load BLIP Model and Processor once at startup
processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", use_fast=True)
model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")


def analyze_image_with_blip(image_path):
    """Analyze the image using BLIP and generate a description."""
    try:
        image = Image.open(image_path).convert("RGB")
        inputs = processor(image, return_tensors="pt")
        out = model.generate(**inputs)
        description = processor.decode(out[0], skip_special_tokens=True)
        return description

    except Exception as e:
        print(f"Error in BLIP processing: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Failed to analyze image: {str(e)}")


def get_myntra_products(query):
    """Scrapes Myntra for products based on the given query using Selenium."""
    stop_words = {"a", "the", "in", "with"}
    query = " ".join([word for word in query.split() if word.lower() not in stop_words])
    url = f"https://www.myntra.com/{query.replace(' ', '-')}"

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.166 Safari/537.36"
    )

    driver = None
    try:
        print(f"Scraping URL: {url}")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get(url)
        time.sleep(5)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        products = [
            {
                "title": item.select_one(".product-product").text.strip(),
                "url": "https://www.myntra.com" + item.select_one("a")["href"],
            }
            for item in soup.select("li.product-base")[:5] if item.select_one(".product-product")
        ]

        return products if products else []

    except Exception as e:
        print(f"Error scraping Myntra: {traceback.format_exc()}")
        return []

    finally:
        if driver:
            driver.quit()


@app.get("/")
def home():
    return {"message": "Welcome to the Outfit Recommendation API!"}


from fastapi.responses import JSONResponse

@app.post("/recommend/")
async def recommend_outfits(file: UploadFile = File(...)):
    try:
        os.makedirs("temp", exist_ok=True)
        image_path = f"temp/{file.filename}"

        with open(image_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        print(f"[DEBUG] Uploaded file saved at: {image_path}")  # Debug print

        description = analyze_image_with_blip(image_path)
        print(f"[DEBUG] Image description: {description}")  # Debug print

        myntra_results = get_myntra_products(description)
        print(f"[DEBUG] Myntra results: {myntra_results}")  # Debug print

        response_data = {
            "status": "success",
            "message": "Recommendations generated successfully.",
            "data": {"description": description, "myntra": myntra_results},
        }

        print(f"[DEBUG] Response Data: {response_data}")  # Debug print
        return JSONResponse(content=response_data)

    except HTTPException as e:
        print(f"[ERROR] HTTP Exception: {str(e)}")  # Debug print
        return JSONResponse(
            status_code=e.status_code,
            content={"status": "error", "message": str(e.detail)},
        )

    except Exception as e:
        print(f"[ERROR] Unexpected server error: {traceback.format_exc()}")  # Debug print
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "Internal Server Error", "details": str(e)},
        )
