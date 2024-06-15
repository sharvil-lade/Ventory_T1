from flask import Flask, request, jsonify, render_template, redirect, url_for
import cv2
import uuid
from PIL import Image
import img2pdf
from firebase_config import bucket, db  # Ensure you have firebase_config set up correctly
import os

app = Flask(__name__)

@app.route('/')
def cm_app():  # Home page route
    certificate_url = request.args.get('certificate_url')
    return render_template('index.html', certificate_url=certificate_url)

def add_text_to_certificate(candidate_name, candidate_id):
    # Define certificate image path
    certificate_image_path = 'blank_certificate.png'
    y = 725  # y-coordinate for the text placement
    font_scale = 4  # Font size
    font = cv2.FONT_HERSHEY_SCRIPT_COMPLEX  # Font style
    thickness = 4  # Font weight
    color = (0, 0, 0)  # Font color (black)

    # Load the certificate image
    image = cv2.imread(certificate_image_path)
    if image is None:
        raise FileNotFoundError(f"Cannot load image from {certificate_image_path}")

    # Get image dimensions
    (image_height, image_width) = image.shape[:2]

    # Get the text size for centering the text
    text_size = cv2.getTextSize(candidate_name, font, font_scale, thickness)[0]
    text_x = (image_width - text_size[0]) // 2  # Center the text horizontally

    # Add text to the image
    cv2.putText(image, candidate_name, (text_x, y), font, font_scale, color, thickness)

    # Ensure the directory for temporary PNGs exists
    os.makedirs('temp_pngs', exist_ok=True)
    png_output_path = f"temp_pngs/{candidate_id}.png"
    cv2.imwrite(png_output_path, image)
    
    if not os.path.exists(png_output_path):
        raise FileNotFoundError(f"Failed to save image at {png_output_path}")

    print(f"Image saved to {png_output_path}")

    # Convert the image to PDF and save it
    os.makedirs('output_pdfs', exist_ok=True)  # Ensure the directory for PDFs exists
    pdf_path = f"output_pdfs/{candidate_id}.pdf"
    image = Image.open(png_output_path)
    pdf_bytes = img2pdf.convert(image.filename)
    
    with open(pdf_path, "wb") as file:
        file.write(pdf_bytes)

    print(f"PDF saved to {pdf_path}")
    image.close()

    return pdf_path

@app.route('/create/', methods=['POST'])
def create():
    try:
        # Extract candidate_name and candidate_email from form data
        candidate_name = request.form.get('candidate_name')[:20]  # Limit name to 20 characters
        candidate_email = request.form.get('candidate_email')
        print(f"Received form data: Name - {candidate_name}, Email - {candidate_email}")

        # Generate a unique ID for the candidate
        candidate_id = uuid.uuid4().hex
        print(f"Generated candidate ID: {candidate_id}")

        # Add text to the certificate
        pdf_path = add_text_to_certificate(candidate_name, candidate_id)
        print(f"Certificate generated and saved to: {pdf_path}")

        # Create a blob object for the PDF file in Firebase Storage
        blob = bucket.blob(f"certificates/{candidate_id}.pdf")

        # Upload the PDF file
        blob.upload_from_filename(pdf_path)
        print(f"Uploaded PDF to Firebase Storage at: certificates/{candidate_id}.pdf")

        # Make the uploaded PDF publicly readable
        blob.make_public()
        print("Made the PDF publicly readable")

        # Get the public URL of the uploaded PDF
        public_url = blob.public_url
        print(f"Public URL of the uploaded PDF: {public_url}")

        # Create a new document in the 'candidates' collection in Firestore
        details = {
            'candidate_name': candidate_name,
            'candidate_email': candidate_email,
            'certificate_url': public_url
        }
        doc_ref = db.collection('candidates').document(candidate_id)
        doc_ref.set(details)
        print(f"Saved details to Firestore: {details}")

        # Redirect to the home page with the certificate URL
        return redirect(url_for('cm_app', certificate_url=public_url))

    except Exception as e:
        print(f"An error occurred: {e}")
        return str(e), 500

@app.route('/certificate/<certificate_id>', methods=['GET'])
def display_certificate(certificate_id):
    try:
        # Retrieve the document reference for the given certificate ID from Firestore
        doc_ref = db.collection('candidates').document(certificate_id)

        # Convert the document reference to a dictionary
        doc = doc_ref.get().to_dict()

        if doc is None:
            return "Certificate not found", 404

        # Get the certificate URL from the document
        certificate_url = doc.get('certificate_url')

        # Render the template with the certificate URL
        return render_template('certificate.html', certificate_url=certificate_url)
    except Exception as e:
        print(f"An error occurred: {e}")
        return str(e), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=3000)
