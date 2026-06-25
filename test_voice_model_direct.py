#!/usr/bin/env python3
"""Direct test of VoiceHistory model without Flask app initialization"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy_models import VoiceHistory
from database import db

def test_voice_history_model_direct():
    """Test VoiceHistory model directly with SQLAlchemy"""
    print("Testing VoiceHistory model directly...")

    # Create in-memory SQLite database for testing
    engine = create_engine('sqlite:///:memory:')

    # Create the VoiceHistory table
    VoiceHistory.__table__.create(engine, checkfirst=True)

    # Create session
    Session = sessionmaker(bind=engine)
    session = Session()

    try:
        # Create a VoiceHistory record
        voice_record = VoiceHistory(
            entity_type='customer',
            entity_id=123,
            audio_filename='test_message.wav',
            audio_file_size=1024000,
            audio_duration_seconds=45.5,
            transcription='This is a test transcription of the voice message.',
            transcription_confidence=0.92,
            language_detected='en',
            ai_model_used='gemini-pro',
            processing_status='completed'
        )

        # Add and commit
        session.add(voice_record)
        session.commit()

        # Retrieve and verify
        retrieved = session.query(VoiceHistory).filter_by(entity_type='customer', entity_id=123).first()
        assert retrieved is not None, "VoiceHistory record not found"
        assert retrieved.entity_type == 'customer'
        assert retrieved.entity_id == 123
        assert retrieved.audio_filename == 'test_message.wav'
        assert retrieved.audio_file_size == 1024000
        assert retrieved.audio_duration_seconds == 45.5
        assert retrieved.transcription == 'This is a test transcription of the voice message.'
        assert retrieved.transcription_confidence == 0.92
        assert retrieved.language_detected == 'en'
        assert retrieved.ai_model_used == 'gemini-pro'
        assert retrieved.processing_status == 'completed'
        assert retrieved.created_at is not None
        assert retrieved.updated_at is not None
        print("[PASS] VoiceHistory record created and retrieved successfully")

        # Test to_dict method
        result_dict = retrieved.to_dict()
        assert isinstance(result_dict, dict)
        assert result_dict['entity_type'] == 'customer'
        assert result_dict['entity_id'] == 123
        assert result_dict['audio_filename'] == 'test_message.wav'
        assert result_dict['transcription'] == 'This is a test transcription of the voice message.'
        assert result_dict['transcription_confidence'] == 0.92
        assert result_dict['language_detected'] == 'en'
        assert result_dict['ai_model_used'] == 'gemini-pro'
        assert result_dict['processing_status'] == 'completed'
        assert 'created_at' in result_dict
        assert 'updated_at' in result_dict
        print("[PASS] VoiceHistory.to_dict() method works correctly")

        # Test soft delete
        retrieved.is_deleted = True
        from datetime import datetime
        retrieved.deleted_at = datetime.utcnow()
        session.commit()

        # Verify soft delete
        assert retrieved.is_deleted == True
        assert retrieved.deleted_at is not None
        print("[PASS] VoiceHistory soft delete functionality works")

        print("\n[SUCCESS] All VoiceHistory model tests passed!")
        return True

    except Exception as e:
        print(f"[FAIL] Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

if __name__ == '__main__':
    success = test_voice_history_model_direct()
    sys.exit(0 if success else 1)