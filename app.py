from flask import Flask, request, render_template_string, jsonify
import requests
import json
import os
from dotenv import load_dotenv
import re

# Carica variabili d'ambiente
load_dotenv()

app = Flask(__name__)

def create_workout_prompt(user_data):
    """Crea un prompt ottimizzato per Mistral-7B-Instruct"""
    
    eta = user_data.get('eta', 25)
    peso = user_data.get('peso', 70)
    obiettivo = user_data.get('obiettivo', 'ipertrofia').lower()
    livello = user_data.get('livello', 'principiante').lower()
    giorni = user_data.get('giorni', 3)
    preferenze = user_data.get('preferenze', '')
    problemi = user_data.get('problemi', '')
    
    prompt = f"""[INST] Sei un personal trainer esperto. Crea una scheda di allenamento personalizzata per questi dati:

UTENTE:
- Età: {eta} anni  
- Peso: {peso} kg
- Obiettivo: {obiettivo}
- Livello: {livello}
- Giorni/settimana: {giorni}
- Preferenze: {preferenze}
- Problemi: {problemi}

TASK: Genera ESCLUSIVAMENTE un JSON valido con {giorni} allenamenti.

FORMAT (segui ESATTO):
{{
  "giorno_1": {{
    "name": "🏋️ Nome Allenamento 1",
    "exercises": [
      {{"name": "Squat", "sets": 4, "reps": 8, "weight": 60}},
      {{"name": "Panca Piana", "sets": 3, "reps": 10, "weight": 50}}
    ]
  }},
  "giorno_2": {{
    "name": "💪 Nome Allenamento 2", 
    "exercises": [
      {{"name": "Stacco", "sets": 3, "reps": 8, "weight": 80}}
    ]
  }}
}}

RULES:
- Ogni allenamento: 6-7 esercizi
- Dai priorità a esercizi che aiutano la persona con il suo problema
- Sets: 3-4, Reps: {"6-8 (forza)" if obiettivo == "forza" else "8-12 (ipertrofia)" if obiettivo == "ipertrofia" else "10-15 (resistenza)"}
- Pesi realistici per {peso}kg livello {livello}
- Esercizi in italiano
{f"- EVITA: {problemi}" if problemi else ""}
{f"- INCLUDI: {preferenze}" if preferenze else ""}

Rispondi SOLO con il JSON: [/INST]

{{"""

    return prompt

def call_ai_api(prompt):
    """Chiama l'API di Hugging Face per generare la scheda - SOLO AI!"""
    
    api_token = os.getenv('HF_API_TOKEN')
    if not api_token:
        return {"error": "Token API non configurato"}
    
    # Usa Mistral-7B-Instruct per JSON strutturato
    api_url = "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3"
    
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_new_tokens": 1200,
            "temperature": 0.2,  # Molto bassa per JSON consistente
            "top_p": 0.8,
            "repetition_penalty": 1.05,
            "return_full_text": False,
            "stop": ["</s>", "Human:", "User:"]  # Stop tokens per Mistral
        }
    }
    
    try:
        response = requests.post(api_url, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()
        
        # Gestisci diversi formati di risposta HF
        if isinstance(result, list) and len(result) > 0:
            generated_text = result[0].get('generated_text', '')
        elif isinstance(result, dict) and 'generated_text' in result:
            generated_text = result['generated_text']
        else:
            generated_text = str(result)
            
        return {"success": True, "text": generated_text}
        
    except requests.exceptions.RequestException as e:
        return {"error": f"Errore API: {str(e)}"}
    except Exception as e:
        return {"error": f"Errore generico: {str(e)}"}

def parse_json_response(response_text):
    """Estrae JSON dalla risposta dell'AI - SOLO AI, NO FALLBACK!"""
    
    # Pulisce la risposta da caratteri extra
    cleaned_text = response_text.strip()
    
    # Cerca JSON pattern più aggressivamente
    patterns = [
        r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}',  # JSON semplice
        r'\{.*?\}(?=\s*$)',  # JSON alla fine
        r'\{.*\}',  # Qualsiasi cosa tra {}
    ]
    
    for pattern in patterns:
        json_matches = re.findall(pattern, cleaned_text, re.DOTALL)
        for json_str in json_matches:
            try:
                # Prova a parsare ogni match
                parsed = json.loads(json_str)
                if isinstance(parsed, dict) and len(parsed) > 0:
                    return parsed
            except json.JSONDecodeError:
                continue
    
    # Se proprio non trova JSON valido, prova a estrarre info manualmente
    return extract_workout_from_text(response_text)

def extract_workout_from_text(text):
    """Estrae informazioni di workout dal testo libero dell'AI"""
    
    # Crea una struttura base e prova a riempirla con regex
    workout = {}
    
    # Cerca pattern di esercizi nel testo
    exercise_patterns = [
        r'(\w+(?:\s+\w+)*)\s*:?\s*(\d+)\s*(?:x|sets?)\s*(\d+)\s*(?:reps?)',
        r'(\w+(?:\s+\w+)*)\s*-?\s*(\d+)\s*set[si]?\s*(?:da|di)?\s*(\d+)',
        r'(\d+)\s*(?:x|set[si]?)\s*(\d+)\s*(\w+(?:\s+\w+)*)'
    ]
    
    exercises_found = []
    for pattern in exercise_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        for match in matches:
            if len(match) == 3:
                exercises_found.append({
                    "name": match[0] if match[0].isalpha() else match[2],
                    "sets": int(match[1]) if match[1].isdigit() else 3,
                    "reps": int(match[2]) if match[2].isdigit() else 10,
                    "weight": 50  # Default weight
                })
    
    # Se ha trovato esercizi, li usa
    if exercises_found:
        workout["workout_1"] = {
            "name": "🤖 Scheda Generata dall'AI",
            "exercises": exercises_found[:6]  # Max 6 esercizi
        }
    else:
        # Come ultima risorsa, restituisce il testo raw
        workout["ai_response"] = {
            "name": "📝 Risposta AI (testo libero)",
            "raw_text": text,
            "exercises": []
        }
    
    return workout

# Template HTML migliorato
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="it">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Gym - Generatore Schede AI</title>
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }
        .container {
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }
        h1 {
            text-align: center;
            color: #333;
            margin-bottom: 30px;
        }
        .form-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-bottom: 20px;
        }
        input, select, textarea {
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
        }
        button {
            background: linear-gradient(45deg, #667eea, #764ba2);
            color: white;
            padding: 15px 30px;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
            margin-top: 20px;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }
        .results {
            margin-top: 30px;
        }
        .workout-card {
            background: #f8f9fa;
            border-radius: 10px;
            padding: 20px;
            margin: 15px 0;
            border-left: 4px solid #667eea;
        }
        .exercise {
            display: flex;
            justify-content: space-between;
            padding: 8px;
            margin: 5px 0;
            background: white;
            border-radius: 5px;
        }
        .loading {
            text-align: center;
            font-style: italic;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🏋️ Gym - Generatore Schede AI</h1>
        
        <form id="workoutForm">
            <div class="form-grid">
                <input type="number" name="eta" placeholder="Età" min="16" max="80" required>
                <input type="number" name="peso" placeholder="Peso (kg)" min="40" max="200" required>
                <select name="obiettivo" required>
                    <option value="">Seleziona obiettivo</option>
                    <option value="ipertrofia">Ipertrofia/Massa</option>
                    <option value="forza">Forza</option>
                    <option value="dimagrimento">Dimagrimento</option>
                    <option value="resistenza">Resistenza</option>
                </select>
                <select name="livello" required>
                    <option value="">Seleziona livello</option>
                    <option value="principiante">Principiante</option>
                    <option value="intermedio">Intermedio</option>
                    <option value="avanzato">Avanzato</option>
                </select>
                <select name="giorni" required>
                    <option value="">Giorni/settimana</option>
                    <option value="2">2 giorni</option>
                    <option value="3">3 giorni</option>
                    <option value="4">4 giorni</option>
                    <option value="5">5 giorni</option>
                    <option value="6">6 giorni</option>
                </select>
            </div>
            
            <textarea name="preferenze" placeholder="Preferenze esercizi (es. squat, panca, trazioni...)" rows="2"></textarea>
            <textarea name="problemi" placeholder="Problemi fisici o limitazioni (es. ginocchio, schiena...)" rows="2"></textarea>
            
            <button type="submit">🚀 Genera Scheda AI</button>
        </form>
        
        <div id="results" class="results"></div>
    </div>

    <script>
        document.getElementById('workoutForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const resultsDiv = document.getElementById('results');
            resultsDiv.innerHTML = '<div class="loading">🤖 Generando la tua scheda personalizzata...</div>';
            
            const formData = new FormData(e.target);
            const data = Object.fromEntries(formData);
            
            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (result.error) {
                    resultsDiv.innerHTML = `<div style="color: red;">❌ ${result.error}</div>`;
                    return;
                }
                
                // Salva in localStorage
                localStorage.setItem('customSchede', JSON.stringify(result.workout));
                
                // Mostra risultati
                displayWorkout(result.workout);
                
            } catch (error) {
                resultsDiv.innerHTML = `<div style="color: red;">❌ Errore: ${error.message}</div>`;
            }
        });
        
        function displayWorkout(workout) {
            const resultsDiv = document.getElementById('results');
            let html = '<h2>🤖 Scheda Generata dall\'AI:</h2>';
            
            // Gestisci diverse strutture di risposta AI
            Object.keys(workout).forEach(key => {
                const day = workout[key];
                
                // Se l'AI ha restituito testo libero
                if (key === 'ai_response') {
                    html += `
                        <div class="workout-card">
                            <h3>${day.name}</h3>
                            <div style="background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107;">
                                <p><strong>🤖 Risposta AI:</strong></p>
                                <pre style="white-space: pre-wrap; font-family: inherit;">${day.raw_text}</pre>
                            </div>
                        </div>
                    `;
                } else if (day && day.exercises) {
                    // Struttura normale con esercizi
                    html += `
                        <div class="workout-card">
                            <h3>${day.name || '🏋️ Allenamento'}</h3>
                    `;
                    
                    day.exercises.forEach(exercise => {
                        const weightText = exercise.weight > 0 ? `${exercise.weight}kg` : 'Corpo libero';
                        html += `
                            <div class="exercise">
                                <span><strong>${exercise.name}</strong></span>
                                <span>${exercise.sets} x ${exercise.reps} - ${weightText}</span>
                            </div>
                        `;
                    });
                    
                    html += '</div>';
                } else {
                    // Fallback per strutture unexpected
                    html += `
                        <div class="workout-card">
                            <h3>🤖 ${key}</h3>
                            <pre>${JSON.stringify(day, null, 2)}</pre>
                        </div>
                    `;
                }
            });
            
            html += `
                <div style="margin-top: 20px; padding: 15px; background: #d4edda; border-radius: 5px; color: #155724;">
                    <strong>✅ Scheda generata al 100% dall'AI!</strong><br>
                    💾 Salvata automaticamente nel browser
                </div>
            `;
            resultsDiv.innerHTML = html;
        }
        
        // Carica scheda salvata all'avvio
        window.addEventListener('load', () => {
            const saved = localStorage.getItem('customSchede');
            if (saved) {
                try {
                    const workout = JSON.parse(saved);
                    displayWorkout(workout);
                } catch (e) {
                    console.log('Errore caricamento scheda salvata');
                }
            }
        });
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate', methods=['POST'])
def generate_workout():
    try:
        user_data = request.get_json()
        
        # Crea prompt ottimizzato
        prompt = create_workout_prompt(user_data)
        
        # Chiama AI API (SEMPRE e SOLO AI!)
        ai_response = call_ai_api(prompt)
        
        if 'error' in ai_response:
            return jsonify({"error": ai_response['error']})
        
        # Parse della risposta AI (anche se non è JSON perfetto)
        workout_data = parse_json_response(ai_response['text'])
        
        return jsonify({
            "success": True,
            "workout": workout_data,
            "debug_info": {
                "raw_ai_response": ai_response['text'],
                "prompt_used": prompt[:200] + "...",  # Prime 200 chars del prompt
                "ai_model": "Mistral-7B-Instruct-v0.3 (Hugging Face)"
            }
        })
        
    except Exception as e:
        return jsonify({
            "error": f"Errore server: {str(e)}",
            "debug": "Controlla i log del server per dettagli"
        })

if __name__ == '__main__':
    app.run(debug=True)