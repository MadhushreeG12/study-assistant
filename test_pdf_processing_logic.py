from main import generate_narration_script
import unittest
from unittest.mock import patch, MagicMock

class TestPDFProcessing(unittest.TestCase):
    @patch('main.summarize_with_groq')
    def test_generate_narration_script_long_text(self, mock_summarize):
        # Mock summarize_with_groq to return a simple string
        mock_summarize.return_value = "Summary Chunk"

        # Create a dummy large text (approx 50k chars, ~15-20 pages)
        large_text = "This is a sentence. " * 2500 
        
        # Call the function
        result = generate_narration_script(large_text)
        
        # Verify that summarize_with_groq was called multiple times (chunking happened)
        # 12000 chars per chunk. 50000 / 12000 = ~5 calls
        print(f"Call count: {mock_summarize.call_count}")
        self.assertTrue(mock_summarize.call_count >= 4, "Should have chunked the large text")
        
        print("Test passed: Long text was chunked and processed!")

if __name__ == '__main__':
    unittest.main()
