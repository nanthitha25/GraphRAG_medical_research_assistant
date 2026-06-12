import os
import json
from openai import OpenAI

class EntityExtractor:
    def __init__(self):
        # Initialize OpenAI client if key is available in environment
        self.api_key = os.environ.get("OPENAI_API_KEY")
        if self.api_key:
            self.client = OpenAI(
                api_key=self.api_key,
                base_url=os.environ.get("OPENAI_BASE_URL")
            )
        else:
            self.client = None
            print("WARNING: OPENAI_API_KEY not found in environment. EntityExtractor will use mock responses.")

    def extract(self, text: str):
        """
        Extracts medical entities and relationships from unstructured text.
        Returns a dictionary with 'entities' and 'relationships'.
        """
        if not self.client:
            return self._mock_extraction(text)

        prompt = f"""
        Extract medical entities and relationships from the following text.
        
        Rules:
        - Return valid JSON only.
        - Include entity types. Standard types: Disease, Drug, Symptom, Organ, Treatment.
        - Use concise relationship labels. Standard relationships: CAUSES, TREATS, AFFECTS, ASSOCIATED_WITH.
        
        Format the output as a strict JSON object with two keys:
        1. "entities": a list of objects, each with "name" and "type".
        2. "relationships": a list of objects, each with "source" (entity name), "relation" (UPPERCASE), and "target" (entity name).

        Text: "{text}"
        """

        try:
            response = self.client.chat.completions.create(
                model="gemini-3.5-flash",
                messages=[
                    {"role": "system", "content": "You are a medical natural language processing AI. Output only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                response_format={ "type": "json_object" },
                temperature=0.0
            )
            
            content = response.choices[0].message.content
            return json.loads(content)
            
        except Exception as e:
            print(f"Error during LLM extraction: {e}")
            return {"entities": [], "relationships": []}

    def _mock_extraction(self, text: str):
        """A simple mock to allow the pipeline to run without an OpenAI key."""
        if "Insulin" in text and "diabetes" in text.lower():
            return {
                "entities": [
                    {"name": "Insulin", "type": "Treatment"},
                    {"name": "Diabetes", "type": "Disease"}
                ],
                "relationships": [
                    {"source": "Insulin", "relation": "TREATS", "target": "Diabetes"}
                ]
            }
        elif "Diabetes" in text and ("kidney" in text.lower() or "kidneys" in text.lower()):
            return {
                "entities": [
                    {"name": "Diabetes", "type": "Disease"},
                    {"name": "Kidney Disease", "type": "Disease"},
                    {"name": "Kidneys", "type": "Organ"}
                ],
                "relationships": [
                    {"source": "Diabetes", "relation": "CAUSES", "target": "Kidney Disease"},
                    {"source": "Diabetes", "relation": "AFFECTS", "target": "Kidneys"}
                ]
            }
        
        return {"entities": [], "relationships": []}
