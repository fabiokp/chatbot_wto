import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import json
import io # Added for PDF handling
try: # Added for PDF handling
    import PyPDF2 # Added for PDF handling
except ImportError:
    print("PyPDF2 library not found. Please install it using: pip install pypdf2")
    PyPDF2 = None

def scrape_simplified_links():
    """
    Scrapes links from the WTO legal texts page, associating them with the
    immediately preceding h2 or h3 header. Filters out anchor links.
    """
    url = "https://www.wto.org/english/docs_e/legal_e/legal_e.htm"
    try:
        response = requests.get(url)
        response.raise_for_status()  # Ensure the request was successful
    except requests.exceptions.RequestException as e:
        print(f"Error fetching URL {url}: {e}")
        return []

    soup = BeautifulSoup(response.text, 'html.parser')
    main_content = soup.find('div', id='mainContent')

    if not main_content:
        print("Could not find the main content div with id='mainContent'")
        return []

    results = []
    current_header = None

    # Iterate through all direct children or specific tags if structure is known
    # Using find_all helps capture elements regardless of nesting depth within mainContent
    for element in main_content.find_all(['h2', 'h3', 'h4', 'a']): # Added 'h4'
        if element.name in ['h2', 'h3', 'h4']: # Added 'h4'
            # Update the current header text, cleaning whitespace and non-breaking spaces
            current_header = element.get_text(strip=True).replace('\xa0', ' ')
        elif element.name == 'a' and element.has_attr('href'):
            link_href = element['href']
            # Ignore javascript links or potentially empty links
            if link_href and "javascript" not in link_href.lower():
                full_link = urljoin(url, link_href)
                # Filter out links containing '#' (anchor links)
                if '#' in full_link:
                    continue

                link_text = element.get_text(strip=True).replace('\xa0', ' ')

                # Only add if we have a valid header context and link text
                if current_header and link_text:
                    results.append({
                        "document": current_header,
                        "title": link_text,
                        "link": full_link
                    })

    return results

def edit_scraped_links(data):
    """
    Applies specific ad-hoc edits to the scraped data list.
    """
    edited_data = []
    for item in data:
        # Edit 1: Remove specific 'original, unamended version' under Annex 1C
        if item['document'].startswith('Annex 1C') and item['title'] == 'original, unamended  version':
            continue  # Skip adding this item to the new list

        # Edit 2: Replace link for 'amended on 23 January 2017' under Annex 1C
        if item['document'].startswith('Annex 1C') and item['title'] == 'amended on 23 January 2017':
            item['link'] = 'https://www.wto.org/english/docs_e/legal_e/trips_e.htm'

        edited_data.append(item)

    # Prepend the new dictionary
    edited_data.insert(0, {
        "document": "Introduction",
        "title": "WTO Legal Texts",
        "link": "https://www.wto.org/english/docs_e/legal_e/legal_e.htm"
    })

    return edited_data

    
    
def scrape_content_for_links(data):
    """
    Scrapes content for each link in the data list.
    Handles HTML (.htm, .html) and PDF (.pdf) files.
    """
    if not PyPDF2:
        print("Cannot process PDFs because PyPDF2 library is not available.")

    for item in data:
        link = item.get('link')
        content = None
        print(f"Processing link: {link}") # Added for progress tracking

        if not link:
            item['content'] = None
            continue

        try:
            # Handle HTML links
            if link.lower().endswith(('.htm', '.html')):
                response = requests.get(link, timeout=10)
                response.raise_for_status()
                soup = BeautifulSoup(response.text, 'html.parser')
                center_col = soup.find('div', class_='centerCol')
                if center_col:
                    # Extract text, clean up whitespace and non-breaking spaces
                    content = ' '.join(center_col.get_text(separator=' ', strip=True).split()).replace('\xa0', ' ')
                else:
                     print(f"Warning: 'centerCol' div not found for HTML link: {link}")


            # Handle PDF links
            elif link.lower().endswith('.pdf') and PyPDF2:
                response = requests.get(link, timeout=30) # Longer timeout for PDFs
                response.raise_for_status()
                # Check if the content type is actually PDF
                if 'application/pdf' in response.headers.get('Content-Type', '').lower():
                    pdf_file = io.BytesIO(response.content)
                    try:
                        reader = PyPDF2.PdfReader(pdf_file)
                        pdf_texts = [page.extract_text() for page in reader.pages if page.extract_text()]
                        content = ' '.join(' '.join(pdf_texts).split()).replace('\xa0', ' ') # Clean text
                    except Exception as pdf_e:
                        print(f"Error reading PDF content from {link}: {pdf_e}")
                else:
                    print(f"Warning: Link ends with .pdf but content type is not PDF: {link}")

            # Add other file type handlers here if needed

        except requests.exceptions.RequestException as e:
            print(f"Error fetching URL {link}: {e}")
        except Exception as e:
            print(f"An unexpected error occurred while processing {link}: {e}")

        item['content'] = content if content else "" # Assign scraped content or empty string

    return data


if __name__ == "__main__":
    scraped_data = scrape_simplified_links()
    if scraped_data:
        # Apply ad-hoc edits
        edited_scraped_data = edit_scraped_links(scraped_data)

        # Scrape content for links
        print("\nStarting content scraping...")
        content_added_data = scrape_content_for_links(edited_scraped_data)
        print("Content scraping finished.\n")

        # Optional: Print the results or save to a file
        # print(json.dumps(content_added_data, indent=4, ensure_ascii=False))

        # Example: Save to a JSON file
        output_filename = "wto_links_with_content.json" # Changed filename
        try:
            with open(output_filename, 'w', encoding='utf-8') as f:
                json.dump(content_added_data, f, ensure_ascii=False, indent=4) # Use data with content
            print(f"Successfully saved simplified links with content to {output_filename}")
        except IOError as e:
            print(f"Error saving data to {output_filename}: {e}")
    else:
        print("No data was scraped.")


        # Count the number of words in all 'content' items
        total_word_count = 0
        for item in content_added_data:
            content = item.get('content', '')
            if content:
                total_word_count += len(content.split())

        print(f"Total word count in all 'content' items: {total_word_count}")
        
        
        # Count the number of words in all 'conteudo' items in transformed_links.json
        input_filename = "wto_links_with_content.json"

        try:
            with open(input_filename, 'r', encoding='utf-8') as f:
                transformed_links = json.load(f)

            total_word_count = 0
            for item in transformed_links:
                conteudo = item.get('content', '')
                if conteudo:
                    total_word_count += len(conteudo.split())

            print(f"Total word count in all 'conteudo' items: {total_word_count}")
        except IOError as e:
            print(f"Error reading data from {input_filename}: {e}")
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {input_filename}: {e}")