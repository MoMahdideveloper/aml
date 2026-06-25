import pytest
from sqlalchemy_models import User

def test_register_and_login_flow(client, app):
    """
    Verify that user registration and login work correctly after removing
    Wallet, Subscription, and Agency models.
    """
    # 1. Register a new user
    response = client.post("/auth/register", data={
        "username": "newuser",
        "email": "newuser@example.com",
        "password": "password123",
        "confirm_password": "password123",
        "full_name": "New User",
        "phone": "1234567890",
        "role": "agent"
    }, follow_redirects=True)
    
    # Registration redirects to login with a success message
    assert response.status_code == 200
    assert b"Account created successfully" in response.data or b"Sign in" in response.data

    # Verify User created in DB
    with app.app_context():
        user = User.query.filter_by(username="newuser").first()
        assert user is not None
        assert user.email == "newuser@example.com"
        
        # Verify removed relationships/fields are gone
        assert not hasattr(user, 'wallet')
        assert not hasattr(user, 'agency')
        assert not hasattr(user, 'subscriptions')
        # hasattr check on instance might check instance dict, let's check class?
        # Actually accessing it usually raises AttributeError if descriptor is gone.
        with pytest.raises(AttributeError):
             _ = user.agency
        with pytest.raises(AttributeError):
             _ = user.wallet

    # 2. Login
    response = client.post("/auth/login", data={
        "username": "newuser",
        "password": "password123"
    }, follow_redirects=True)

    assert response.status_code == 200
    # Should redirect to dashboard
    assert b"Dashboard" in response.data or b"Overview" in response.data

    # 3. Check Profile Page
    response = client.get("/auth/profile")
    assert response.status_code == 200
    content = response.data.decode('utf-8')
    
    # Ensure simplified profile renders
    assert "New User" in content
    # Ensure removed sections are NOT present
    assert "Wallet" not in content
    assert "Subscription" not in content
    assert "Agency" not in content
