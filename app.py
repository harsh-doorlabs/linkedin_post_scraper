from flask import Flask, request, send_file, render_template_string, make_response
import csv
import io
from bs4 import BeautifulSoup

app = Flask(__name__)

# -------------------------------
# 1) Your original Python function
# -------------------------------
def extract_post_data_from_html_content(html_content):
    """
    This is a refactored version of your existing code that takes
    in a string of HTML content (instead of reading from a file)
    and returns a list of dictionaries with the extracted fields.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    extracted_data = []

    # Adjust the class as needed, e.g. 'JCniPHMkzeWTJVYtYcBxPACGcXOBjlBoflxc'
    post_items = soup.find_all('li', class_='JCniPHMkzeWTJVYtYcBxPACGcXOBjlBoflxc')

    for post in post_items:
        # Example fields; adjust to your actual extraction
        reposter_info = post.find('span', class_='update-components-header__text-view')
        reposter_name = reposter_info.get_text(strip=True) if reposter_info else None

        original_poster_tag = post.find('span', class_='kgDPXkLQKouRClQPVOdEYtMnqfCCpJTUntJk')
        original_poster = original_poster_tag.get_text(strip=True) if original_poster_tag else None

        original_poster_link = None
        if original_poster_tag:
            parent_link = original_poster_tag.find_parent('a', href=True)
            if parent_link:
                original_poster_link = parent_link['href']

        follower_count_span = post.find('span', class_='update-components-actor__description')
        follower_count = follower_count_span.get_text(strip=True) if follower_count_span else None

        time_info_tag = post.find('span', class_='update-components-actor__sub-description')
        posted_time = time_info_tag.get_text(strip=True) if time_info_tag else None

        text_container = post.find('div', class_='feed-shared-inline-show-more-text')
        post_text = text_container.get_text(strip=True) if text_container else None

        text_links = []
        if text_container:
            link_tags = text_container.find_all('a', href=True)
            text_links = [lt['href'] for lt in link_tags]

        reactions_button = post.find('button', attrs={'data-reaction-details': True})
        total_reactions = None
        if reactions_button and reactions_button.has_attr('aria-label'):
            total_reactions = reactions_button['aria-label']

        comments_button = post.find(
            'button',
            attrs={'aria-label': lambda val: val and "comments" in val}
        )
        total_comments = comments_button['aria-label'] if comments_button else None

        reposts_button = post.find(
            'button',
            attrs={'aria-label': lambda val: val and "reposts" in val}
        )
        total_reposts = reposts_button['aria-label'] if reposts_button else None

        video_tag = post.find('video')
        video_src = video_tag['src'] if (video_tag and video_tag.has_attr('src')) else None
        video_poster = video_tag['poster'] if (video_tag and video_tag.has_attr('poster')) else None

        # Simple post type detection
        post_type = "text"
        video_section = post.find('div', class_='update-components-linkedin-video')
        if video_section or video_tag:
            post_type = "video"
        else:
            carousel_section = post.find('div', class_='feed-shared-update-v2--with-carousel-fix')
            if carousel_section:
                post_type = "carousel"
            else:
                image_tags = post.find_all('img')
                non_profile_images = [
                    img for img in image_tags
                    if not any(
                        sub in (img.get('src','') + str(img.get('class','')))
                        for sub in ['profile-displayphoto', 'EntityPhoto']
                    )
                ]
                if non_profile_images:
                    post_type = "image"

        extracted_data.append({
            'reposter_name': reposter_name,
            'original_poster': original_poster,
            'original_poster_link': original_poster_link,
            'follower_count': follower_count,
            'posted_time': posted_time,
            'post_text': post_text,
            'text_links': "; ".join(text_links) if text_links else None,
            'total_reactions': total_reactions,
            'total_comments': total_comments,
            'total_reposts': total_reposts,
            'video_src': video_src,
            'video_poster': video_poster,
            'post_type': post_type
        })

    return extracted_data


# -------------------------------
# 2) Create the Flask routes
# -------------------------------

# A simple HTML form so you can upload a file via browser
UPLOAD_FORM_HTML = """
<!doctype html>
<html>
  <head>
    <title>Upload LinkedIn Post HTML (.txt)</title>
  </head>
  <body>
    <h1>Upload a .txt file containing LinkedIn post HTML</h1>
    <form action="/upload" method="post" enctype="multipart/form-data">
      <p><input type="file" name="file" accept=".txt"></p>
      <p><button type="submit">Upload & Extract</button></p>
    </form>
  </body>
</html>
"""

@app.route('/', methods=['GET'])
def index():
    # Show a simple form
    return render_template_string(UPLOAD_FORM_HTML)

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Receives the uploaded file, parses the HTML content,
    and returns a CSV file as the HTTP response.
    """
    if 'file' not in request.files:
        return "No file found in the request", 400

    file = request.files['file']
    if file.filename == '':
        return "No selected file", 400

    # Read the text from the uploaded file
    html_content = file.read().decode('utf-8', errors='replace')

    # Extract data using your logic
    extracted_data = extract_post_data_from_html_content(html_content)

    # Convert the extracted data to CSV in-memory
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=[
        'reposter_name',
        'original_poster',
        'original_poster_link',
        'follower_count',
        'posted_time',
        'post_text',
        'text_links',
        'total_reactions',
        'total_comments',
        'total_reposts',
        'video_src',
        'video_poster',
        'post_type'
    ])
    writer.writeheader()
    for row in extracted_data:
        writer.writerow(row)

    csv_content = output.getvalue()
    output.close()

    # Return a response with appropriate headers to prompt download
    response = make_response(csv_content)
    response.headers["Content-Disposition"] = "attachment; filename=extracted_posts.csv"
    response.headers["Content-Type"] = "text/csv"
    return response

if __name__ == '__main__':
    app.run(debug=True)
