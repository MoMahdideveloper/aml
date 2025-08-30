# Real Estate CRM System

## Overview

This is a comprehensive Real Estate Customer Relationship Management (CRM) system built with Flask. The application helps real estate agencies manage properties, agents, customers, deals, and tasks while providing AI-powered property recommendations using Google Gemini. The system features a clean web interface for managing all aspects of real estate operations, from property listings to deal tracking and customer relationship management.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Backend Architecture
- **Framework**: Flask-based web application with a modular structure
- **Data Layer**: In-memory data management using Python dictionaries and classes
- **Model Layer**: Object-oriented design with separate model classes for Property, Agent, Customer, Deal, and Task entities
- **Service Layer**: Dedicated service classes for external integrations (GeminiService for AI recommendations)
- **Routing**: Centralized route management in routes.py with proper separation of concerns

### Frontend Architecture
- **Template Engine**: Jinja2 templating with a base template for consistent layout
- **UI Framework**: Bootstrap 5 for responsive design and components
- **Styling**: Custom CSS with CSS variables for theming and consistent design language
- **JavaScript**: Vanilla JavaScript for client-side interactions and form handling
- **Layout Pattern**: Fixed sidebar navigation with main content area

### Data Storage
- **Current Implementation**: In-memory storage using Python dictionaries with auto-incrementing IDs
- **Data Models**: Structured classes with type hints and serialization methods
- **Sample Data**: Initialization with realistic sample data for demonstration purposes
- **Data Manager**: Centralized data access layer with CRUD operations for all entities

### Authentication & Authorization
- **Session Management**: Flask sessions with configurable secret key
- **Security**: Environment-based configuration for sensitive data
- **Access Control**: Currently designed for single-tenant usage without role-based access

## External Dependencies

### AI Integration
- **Google Gemini API**: Used for intelligent property recommendations based on customer preferences
- **Service Pattern**: Dedicated GeminiService class handles all AI-related operations
- **Recommendation Engine**: Matches customer profiles with available properties using natural language processing

### Frontend Libraries
- **Bootstrap 5**: Complete UI component library and responsive grid system
- **Font Awesome 6**: Icon library for consistent iconography throughout the application
- **Google Fonts**: Inter font family for modern typography

### Development Tools
- **Flask**: Core web framework with debug mode for development
- **Python Type Hints**: Enhanced code reliability and IDE support
- **Logging**: Built-in Python logging for debugging and monitoring

### Environment Configuration
- **Session Secret**: Configurable via SESSION_SECRET environment variable
- **Gemini API Key**: Required GEMINI_API_KEY environment variable for AI features
- **Development Mode**: Debug mode enabled for development with hot reloading
<!-- Update OWNER/REPO with your GitHub org and repo name -->
[![CI](https://github.com/OWNER/REPO/actions/workflows/tests.yml/badge.svg)](https://github.com/OWNER/REPO/actions/workflows/tests.yml)
