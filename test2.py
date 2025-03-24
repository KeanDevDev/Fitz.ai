import os
import time
import traceback
from PIL import Image
from transformers import BlipProcessor, BlipForConditionalGeneration
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse

# Suppress TensorFlow and Transformers warnings
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_ENABLE_ONEDNN_OPTS"] = "0"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"

# Initialize FastAPI app
app = FastAPI()

# Function to analyze the image using BLIP and generate a description
def analyze_image_with_blip(image_path):
    try:
        # Open the image
        image = Image.open(image_path)
        # Ensure it's a valid image
        image.verify()
        image = Image.open(image_path).convert("RGB")

        # Load the BLIP model and processor
        processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base", use_fast=True)
        model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")

        # Generate a caption
        inputs = processor(image, return_tensors="pt")
        out = model.generate(**inputs)
        description = processor.decode(out[0], skip_special_tokens=True)

        return description

    except Exception as e:
        print(f"Error in BLIP processing: {traceback.format_exc()}")
        raise ValueError(f"Failed to analyze image: {e}")


# Function to scrape Myntra for products using Selenium
def get_myntra_products(query):
    """
    Scrapes Myntra for products based on the given query.
    """
    # Remove stop words from the query
    stop_words = {"a", "the", "in", "with"}
    query = " ".join([word for word in query.split() if word.lower() not in stop_words])
    url = f"https://www.myntra.com/{query.replace(' ', '-')}"

    # Set up Selenium WebDriver with WebDriver Manager
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # Run in headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.6998.166 Safari/537.36")

    # Initialize WebDriver using WebDriver Manager
    driver = None
    try:
        print(f"Scraping URL: {url}")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get(url)
        time.sleep(5)  # Allow time for dynamic content to load

        # Parse the page source with BeautifulSoup
        soup = BeautifulSoup(driver.page_source, "html.parser")

        # Extract product details
        products = []
        for item in soup.select("li.product-base")[:5]:  # Limit results
            try:
                title = item.select_one(".product-product").text.strip() if item.select_one(".product-product") else "N/A"
                link = "https://www.myntra.com" + item.select_one("a")["href"] if item.select_one("a") else "N/A"
                products.append({"title": title, "url": link})
            except Exception as e:
                print(f"Error parsing product: {e}")

        print(f"Scraped Products: {products}")
        return products

    except Exception as e:
        print(f"Error scraping Myntra: {e}")
        return []

    finally:
        if driver:
            driver.quit()

# Home endpoint
@app.get("/")
def home():
    return {"message": "Welcome to the Outfit Recommendation API!"}

# Endpoint to recommend outfits
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import JSONResponse
import os
import traceback

app = FastAPI()

from fastapi import FastAPI, File, UploadFile

app = FastAPI()

@app.post("/upload/")
async def upload_file(file: UploadFile = File(...)):
    return {"filename": file.filename}

@app.post("/recommend/")
async def recommend_outfits(file: UploadFile = File(...)):
    try:
        # Ensure the temp directory exists
        os.makedirs("temp", exist_ok=True)

        # Save the uploaded file
        image_path = f"temp/{file.filename}"
        with open(image_path, "wb") as f:
            f.write(await file.read())

        print(f"Uploaded file saved at: {image_path}")

        # Analyze the image and generate a description using BLIP
        description = analyze_image_with_blip(image_path)
        print(f"Outfit Description: {description}")

        # Search Myntra for products matching the description
        myntra_results = get_myntra_products(description)
        print(f"Myntra Products: {myntra_results}")

        if not myntra_results:
            return {"status": "success", "message": "No products found on Myntra.", "data": {"description": description, "myntra": []}}

        return {"status": "success", "message": "Recommendations generated successfully.", "data": {"description": description, "myntra": myntra_results}}

    except ValueError as ve:
        print(f"ValueError: {ve}")
        raise HTTPException(status_code=400, detail={"status": "error", "message": str(ve)})

    except Exception as e:
        print(f"Unexpected server error: {traceback.format_exc()}")
        return JSONResponse(
            status_code=500,
            content={"status": "error", "message": "An unexpected error occurred. Please try again later.", "details": str(e)}
        )
# Entry point for standalone testing
if __name__ == "__main__":
    # Test the BLIP model with a sample image
    test_image_path = r"D:\Workathon\Flask\balls.jpg"  # Replace with your test image path
    try:
        description = analyze_image_with_blip(test_image_path)
        print(f"Test BLIP Output: {description}")
    except Exception as e:
        print(f"Error testing BLIP model: {e}")

    # Test the Myntra scraping logic with a sample query
    test_query = "blue jeans"
    try:
        products = get_myntra_products(test_query)
        print(f"Test Myntra Output: {products}")
    except Exception as e:
        print(f"Error testing Myntra scraping: {e}")