from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)

# Funzione che genera la scheda di allenamento
def generate_workout(data):
    age = data.get("age")
    weight = data.get("weight")
    goal = data.get("goal")
    activity_level = data.get("activity_level")
    days_per_week = data.get("days_per_week")
    preferences = data.get("preferences", [])
    injuries = data.get("injuries", [])

    workout_plan = []

    # Logica base
    if goal == "perdere peso":
        workout_plan.append("Cardio: 30 minuti a intensità moderata")
        workout_plan.append("Esercizi di forza: 3 set di squat, affondi, push-up")
    elif goal == "aumentare massa":
        workout_plan.append("Esercizi di forza: 4 set di squat, panca, deadlift")
        workout_plan.append("Cardio: 20 minuti a bassa intensità")

    if activity_level == "principiante":
        workout_plan.append("Esercizi a corpo libero: squat, push-up, plank")
    elif activity_level == "intermedio":
        workout_plan.append("Esercizi con pesi leggeri: deadlift, panca, squat")
    elif activity_level == "avanzato":
        workout_plan.append("Esercizi con pesi pesanti: squat, panca, stacco da terra")

    if days_per_week == "3":
        workout_plan.append("Allenamento 3 giorni a settimana: giorno 1 - forza, giorno 2 - cardio, giorno 3 - corpo libero")
    elif days_per_week == "5":
        workout_plan.append("Allenamento 5 giorni a settimana: giorni alternati di forza e cardio")

    if injuries:
        workout_plan.append(f"Aggiustamenti: Evitare esercizi che causano {', '.join(injuries)}")

    if preferences:
        workout_plan.append(f"Preferenze: Include esercizi come {', '.join(preferences)}")

    return workout_plan

# Route per la home page con modulo HTML
@app.route('/')
def home():
    return render_template_string("""
        <h1>Generatore Schede Allenamento</h1>
        <form id="workoutForm">
            Età: <input name="age"><br>
            Peso: <input name="weight"><br>
            Obiettivo: <input name="goal"><br>
            Livello: <input name="activity_level"><br>
            Giorni/settimana: <input name="days_per_week"><br>
            Preferenze (es. squat,push-up): <input name="preferences"><br>
            Problemi fisici (es. ginocchio,schiena): <input name="injuries"><br>
            <button type="submit">Genera Scheda</button>
        </form>
        <h2>La tua scheda:</h2>
        <div id="workoutPlan"></div>

        <script>
        document.getElementById('workoutForm').addEventListener('submit', function(e){
            e.preventDefault();
            let data = {
                age: e.target.age.value,
                weight: e.target.weight.value,
                goal: e.target.goal.value,
                activity_level: e.target.activity_level.value,
                days_per_week: e.target.days_per_week.value,
                preferences: e.target.preferences.value.split(','),
                injuries: e.target.injuries.value.split(',')
            };
            fetch('/generate', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(data)
            })
            .then(res => res.json())
            .then(res => {
                document.getElementById('workoutPlan').innerHTML = '<ul>' + res.workout_plan.map(item => `<li>${item}</li>`).join('') + '</ul>';
            });
        });
        </script>
    """)

# Route per generare la scheda (POST)
@app.route('/generate', methods=['POST'])
def generate():
    data = request.get_json()
    workout_plan = generate_workout(data)
    return jsonify({"workout_plan": workout_plan})

if __name__ == "__main__":
    app.run(debug=True)
