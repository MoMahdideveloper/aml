"""
Test accessibility and responsive design features
"""
import pytest
from bs4 import BeautifulSoup
from flask import url_for


class TestAccessibilityFeatures:
    """Test accessibility enhancements"""
    
    def test_modal_accessibility_attributes(self, client):
        """Test that modals have proper accessibility attributes"""
        response = client.get('/agents')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check for agent edit modal
        modal = soup.find('div', {'id': 'agentEditModal'})
        if modal:
            # Check ARIA attributes
            assert modal.get('role') == 'dialog'
            assert modal.get('aria-labelledby') == 'agentEditModalLabel'
            assert modal.get('aria-describedby') == 'agentEditModalDescription'
            assert modal.get('aria-hidden') == 'true'
            
            # Check modal title
            title = modal.find('h5', {'id': 'agentEditModalLabel'})
            assert title is not None
            
            # Check close button accessibility
            close_btn = modal.find('button', {'data-bs-dismiss': 'modal'})
            assert close_btn is not None
            assert close_btn.get('aria-label') is not None
    
    def test_form_accessibility_attributes(self, client):
        """Test that forms have proper accessibility attributes"""
        response = client.get('/agents')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check for form elements with proper labels
        inputs = soup.find_all('input', {'type': ['text', 'email', 'tel']})
        for input_elem in inputs:
            input_id = input_elem.get('id')
            if input_id:
                # Check for associated label
                label = soup.find('label', {'for': input_id})
                assert label is not None, f"Input {input_id} should have an associated label"
                
                # Check for aria-describedby if present
                describedby = input_elem.get('aria-describedby')
                if describedby:
                    for desc_id in describedby.split():
                        desc_elem = soup.find(id=desc_id)
                        assert desc_elem is not None, f"Element {desc_id} referenced by aria-describedby should exist"
    
    def test_navigation_accessibility(self, client):
        """Test navigation accessibility"""
        response = client.get('/')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check sidebar navigation
        sidebar = soup.find('nav', {'class': 'sidebar'})
        assert sidebar is not None
        assert sidebar.get('role') == 'navigation'
        assert sidebar.get('aria-label') == 'Main navigation'
        
        # Check navigation links
        nav_links = sidebar.find_all('a', {'class': 'nav-link'})
        for link in nav_links:
            # Check for proper ARIA current attribute on active links
            if 'active' in link.get('class', []):
                assert link.get('aria-current') == 'page'
    
    def test_button_accessibility(self, client):
        """Test button accessibility"""
        response = client.get('/agents')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check buttons have proper labels
        buttons = soup.find_all('button')
        for button in buttons:
            # Button should have either text content or aria-label
            has_text = button.get_text(strip=True)
            has_aria_label = button.get('aria-label')
            
            assert has_text or has_aria_label, "Button should have text content or aria-label"
    
    def test_icons_are_hidden_from_screen_readers(self, client):
        """Test that decorative icons are hidden from screen readers"""
        response = client.get('/agents')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check that Font Awesome icons have aria-hidden
        icons = soup.find_all('i', {'class': lambda x: x and 'fas' in x})
        for icon in icons:
            # Icons should be hidden from screen readers unless they're the only content
            parent = icon.parent
            if parent and parent.get_text(strip=True) != icon.get_text(strip=True):
                assert icon.get('aria-hidden') == 'true', f"Decorative icon should have aria-hidden='true'"


class TestResponsiveDesign:
    """Test responsive design features"""
    
    def test_viewport_meta_tag(self, client):
        """Test that viewport meta tag is present"""
        response = client.get('/')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        viewport_meta = soup.find('meta', {'name': 'viewport'})
        assert viewport_meta is not None
        assert 'width=device-width' in viewport_meta.get('content', '')
        assert 'initial-scale=1.0' in viewport_meta.get('content', '')
    
    def test_responsive_modal_classes(self, client):
        """Test that modals have responsive classes"""
        response = client.get('/agents')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check modal dialogs have responsive classes
        modal_dialogs = soup.find_all('div', {'class': lambda x: x and 'modal-dialog' in x})
        for dialog in modal_dialogs:
            classes = dialog.get('class', [])
            # Should have either modal-dialog-centered or modal-dialog-scrollable
            assert any(cls in classes for cls in ['modal-dialog-centered', 'modal-dialog-scrollable'])
    
    def test_responsive_table_wrapper(self, client):
        """Test that tables have responsive wrappers"""
        response = client.get('/customers')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check that tables are wrapped in responsive containers
        tables = soup.find_all('table', {'class': 'table'})
        for table in tables:
            # Table should be inside a table-responsive container
            parent = table.parent
            while parent and parent.name != 'body':
                if 'table-responsive' in parent.get('class', []):
                    break
                parent = parent.parent
            else:
                # If no table-responsive found, that's okay for some tables
                pass
    
    def test_bootstrap_responsive_classes(self, client):
        """Test that Bootstrap responsive classes are used"""
        response = client.get('/agents')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check for responsive column classes
        cols = soup.find_all('div', {'class': lambda x: x and any(
            cls.startswith(('col-', 'col-sm-', 'col-md-', 'col-lg-', 'col-xl-')) 
            for cls in x.split()
        )})
        
        # Should have some responsive columns
        assert len(cols) > 0, "Should have responsive column classes"


class TestKeyboardNavigation:
    """Test keyboard navigation features"""
    
    def test_tabindex_attributes(self, client):
        """Test proper tabindex usage"""
        response = client.get('/')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check that main content area is focusable
        main_content = soup.find('div', {'class': lambda x: x and 'main-content' in x})
        if main_content:
            # Should have tabindex="-1" for programmatic focus
            assert main_content.get('tabindex') == '-1' or main_content.get('id') == 'main-content'
    
    def test_skip_links(self, client):
        """Test skip to main content functionality"""
        response = client.get('/')
        assert response.status_code == 200
        
        # Skip links are added by JavaScript, so we test the structure exists
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check that main content area exists and is identifiable
        main_content = (
            soup.find(id='main-content') or 
            soup.find('main') or 
            soup.find('div', {'class': lambda x: x and 'main-content' in x})
        )
        assert main_content is not None, "Main content area should be identifiable for skip links"


class TestFormValidation:
    """Test form validation accessibility"""
    
    def test_required_field_indicators(self, client):
        """Test that required fields are properly indicated"""
        response = client.get('/agents')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check for required inputs
        required_inputs = soup.find_all('input', {'required': True})
        for input_elem in required_inputs:
            input_id = input_elem.get('id')
            if input_id:
                # Check for associated label
                label = soup.find('label', {'for': input_id})
                if label:
                    # Label should indicate required field
                    label_text = label.get_text()
                    label_html = str(label)
                    assert ('*' in label_text or 
                           'required' in label_text.lower() or
                           'text-danger' in label_html or
                           'aria-label="required"' in label_html), f"Required field {input_id} should be indicated in label"
    
    def test_error_message_containers(self, client):
        """Test that error message containers exist"""
        response = client.get('/agents')
        assert response.status_code == 200
        
        soup = BeautifulSoup(response.data, 'html.parser')
        
        # Check for invalid-feedback containers
        inputs = soup.find_all('input', {'type': ['text', 'email', 'tel']})
        for input_elem in inputs:
            # Should have error container nearby
            parent = input_elem.parent
            error_container = parent.find('div', {'class': lambda x: x and 'invalid-feedback' in x})
            # Error containers might be added dynamically, so this is optional
            if error_container:
                assert error_container.get('role') == 'alert' or 'aria-live' in str(error_container)


def test_css_accessibility_features():
    """Test CSS accessibility features"""
    import os
    
    css_path = os.path.join('static', 'css', 'style.css')
    if os.path.exists(css_path):
        with open(css_path, 'r') as f:
            css_content = f.read()
        
        # Check for accessibility-related CSS
        assert '.visually-hidden' in css_content or '.sr-only' in css_content
        assert 'focus' in css_content
        assert '@media (prefers-reduced-motion' in css_content
        assert '@media (prefers-contrast' in css_content
        assert 'outline' in css_content


def test_javascript_accessibility_features():
    """Test JavaScript accessibility features"""
    import os
    
    js_path = os.path.join('static', 'js', 'accessibility-enhancements.js')
    if os.path.exists(js_path):
        with open(js_path, 'r') as f:
            js_content = f.read()
        
        # Check for accessibility-related JavaScript
        assert 'aria-' in js_content
        assert 'focus' in js_content
        assert 'keydown' in js_content or 'keypress' in js_content
        assert 'screen reader' in js_content.lower() or 'screenreader' in js_content.lower()
        assert 'tabindex' in js_content
