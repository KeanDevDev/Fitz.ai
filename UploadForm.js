import React, { useState } from "react";
import axios from "axios";

function UploadForm() {
    const [file, setFile] = useState(null);
    const [result, setResult] = useState(null);

    const handleFileChange = (event) => {
        setFile(event.target.files[0]);
    };

    const handleUpload = async () => {
        if (!file) {
            alert("Please select a file first!");
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await axios.post("http://127.0.0.1:8000/recommend/", formData, {
                headers: { "Content-Type": "multipart/form-data" }
            });
            setResult(response.data);
        } catch (error) {
            console.error("Error uploading file:", error);
            alert("Failed to upload image.");
        }
    };

    return (
        <div>
            <h2>Upload an Image</h2>
            <input type="file" onChange={handleFileChange} />
            <button onClick={handleUpload}>Upload</button>

            {result && (
                <div>
                    <h3>Results:</h3>
                    <p><strong>Description:</strong> {result.data.description}</p>
                    <h4>Recommended Products:</h4>
                    <ul>
                        {result.data.myntra.map((item, index) => (
                            <li key={index}>
                                <a href={item.url} target="_blank" rel="noopener noreferrer">{item.title}</a>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
        </div>
    );
}

export default UploadForm;
