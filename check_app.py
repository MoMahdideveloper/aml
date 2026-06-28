from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page()
    
    # Console and error logging
    page.on('console', lambda msg: print(f'BROWSER CONSOLE: {msg.text}'))
    page.on('pageerror', lambda err: print(f'PAGE ERROR: {err}'))
    
    # Navigate to the application
    print("Navigating to http://127.0.0.1:5000/")
    page.goto('http://127.0.0.1:5000/', timeout=30000)
    
    # Wait for page to load
    page.wait_for_load_state('networkidle', timeout=10000)
    
    # Get page title
    title = page.title()
    print(f'Page title: {title}')
    
    # Check for navigation links
    nav_links = ['Dashboard', 'Properties', 'Agents', 'Customers']
    for link_text in nav_links:
        link = page.query_selector(f'a:has-text("{link_text}")')
        print(f'{link_text} link found: {link is not None}')
        
        # If link found, test clicking it
        if link:
            try:
                link.click()
                page.wait_for_load_state('networkidle', timeout=5000)
                print(f'  -> Successfully navigated to {link_text} page')
                print(f'  -> New URL: {page.url}')
                print(f'  -> New title: {page.title()}')
                # Go back to main dashboard for next test
                page.go_back()
                page.wait_for_load_state('networkidle', timeout=5000)
            except Exception as e:
                print(f'  -> Error clicking {link_text}: {e}')
    
    # Check for common error indicators
    error_selectors = [
        '.alert-danger',
        '.alert-error', 
        '.error',
        '[class*="error"]',
        '.alert-warning',
        '.warning',
        '.text-danger',
        '.text-danger'
    ]
    
    total_errors = 0
    for selector in error_selectors:
        elements = page.query_selector_all(selector)
        if elements:
            print(f'Found {len(elements)} elements with selector "{selector}"')
            for i, elem in enumerate(elements[:3]):  # Limit output
                text = elem.inner_text()[:100].strip()
                if text:
                    print(f'  Element {i+1} text: {text}')
            total_errors += len(elements)
    
    print(f'Total potential error/warning elements found: {total_errors}')
    
    # Check for forms and input elements
    forms = page.query_selector_all('form')
    print(f'Found {len(forms)} form(s)')
    
    inputs = page.query_selector_all('input, select, textarea')
    print(f'Found {len(inputs)} input/select/textarea element(s)')
    
    # Check for tables or data displays
    tables = page.query_selector_all('table')
    print(f'Found {len(tables)} table(s)')
    
    cards = page.query_selector_all('.card, .panel, .widget')
    print(f'Found {len(cards)} card/panel/widget element(s)')
    
    browser.close()
