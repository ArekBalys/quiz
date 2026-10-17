from flask import Flask, render_template, request, redirect, url_for, session
import yaml
import random
from database import db, Database
from dataclasses import dataclass

@dataclass
class Question:
    question: str
    answers: list
    correct_answer: int

    def __post_init__(self):
        if isinstance(self.correct_answer, list):
            self.correct_answer = self.correct_answer[0] if self.correct_answer else 0
        self.correct_answer = int(self.correct_answer) - 1


class Quiz:
    def __init__(self, total_questions, questions_file="pytania.yaml"):
        self.total_questions = total_questions
        self.questions = []
        self.app = Flask(__name__)
        
        self.app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///quiz.db"
        self.app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
        db.init_app(self.app)

        with self.app.app_context():
            db.create_all()

        # Showcase purpose only :)
        self.app.config["SECRET_KEY"] = "quiz-secret-key"

        try:
            with open(questions_file, "r", encoding="utf-8") as file:
                self.questions = [Question(**q) for q in yaml.safe_load(file).get("questions", [])]
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Nie znaleziono pliku {questions_file}. Upewnij się, że plik istnieje w katalogu projektu."
            )

        # I'm using the class-type Flask app, so I need to add all redirections here
        self.app.add_url_rule('/', view_func=self.hello, methods=['GET', 'POST'])
        self.app.add_url_rule('/quiz', view_func=self.quiz, methods=['GET', 'POST'])
        self.app.add_url_rule('/result', view_func=self.result, methods=['GET', 'POST'])

    def _ensure_session(self):
        """ I need to ensure that the sessions variables are initialized before using them."""
        session.setdefault('name', '')
        session.setdefault('score', 0)
        session.setdefault('iterations', 1)
        session.setdefault('used_questions', [])
        session.setdefault('current_question', None)
        session.setdefault('uwagi', '')

    def save_score(self, username, score, uwagi=""):
        user = Database.query.filter_by(name=username).first()

        if user:
            # Update only if new score is better
            if score > user.best_score:
                user.best_score = score
                user.uwagi = uwagi
        else:
            # Create new record
            user = Database(name=username, best_score=score, uwagi=uwagi)
            db.session.add(user)

        db.session.commit()

    def get_top_scores(self, limit=5):
        # Order by best_score descending, return first N users
        users = Database.query.order_by(Database.best_score.desc()).limit(limit).all()
        return [u.as_dict() for u in users]

    def start(self):
        """ Here is my app starting point, leaving debug=True if you need track the app process"""
        self.app.run(debug=True)

    def reset_quiz(self):
        """ If you request a new quiz, this function is needed to reset the session variables"""
        session['iterations'] = 1
        session['score'] = 0
        session['used_questions'] = []
        session['current_question'] = None
        session['uwagi'] = ""

    def random_question(self):
        """ This function selects a random question that was not used yet"""
        used = session.get('used_questions', [])
        available = [q for q in self.questions if q.question not in [item['question'] for item in used]]

        if not available:
            session['used_questions'] = []
            available = self.questions

        choice = random.choice(available)
        session['current_question'] = {
            'question': choice.question,
            'answers': choice.answers,
            'correct_answer': choice.correct_answer,
        }
        session['used_questions'].append({
            'question': choice.question,
            'answers': choice.answers,
            'correct_answer': choice.correct_answer,
        })

    def hello(self):
        """ Hello page for collecting the user's name and starting the quiz"""
        if request.method == 'POST':
            self._ensure_session()
            print(session['iterations'])
            if session['iterations'] == self.total_questions + 1:
                self.reset_quiz()
                return redirect(url_for('quiz'))
            
            session['name'] = request.form['name']
            session['score'] = 0
            session['iterations'] = 1
            session['used_questions'] = []
            self.random_question()
            return redirect(url_for('quiz'))
        return render_template('hello.html',
            total_questions=self.total_questions,
            best_score=self.get_top_scores()
        )

    def quiz(self):
        """ Quiz page for displaying questions and handling answers"""
        self._ensure_session()

        # Here we go after clicking start quiz button.
        if request.method == 'GET':
            if session.get('current_question') is None:
                self.random_question()
            current = session['current_question']
            return render_template(
                'quiz.html',
                name=session['name'],
                total_questions=self.total_questions,
                question=current['question'],
                answers=current['answers'],
                iteration=session['iterations'],
                best_score=self.get_top_scores()
            )

        if request.method == 'POST':
            current = session.get('current_question')
            if current is not None:
                selected_answer = request.form.get('answer')
                if selected_answer in current['answers']:
                    selected_index = current['answers'].index(selected_answer)
                    if selected_index == current['correct_answer']:
                        session['score'] = session.get('score', 0) + 1

                session['iterations'] = session.get('iterations', 1) + 1
                if session['iterations'] <= self.total_questions:
                    self.random_question()
                    return redirect(url_for('quiz'))

            session['uwagi'] = request.form.get('uwagi', "")

            return redirect(url_for('result'))

    def result(self):
        """ Result page for displaying the final score and allowing a new quiz"""
        self._ensure_session()

        self.save_score(session.get('name' ""), session.get('score', 0))

        return render_template(
            'result.html',
            name=session.get('name' ""),
            score=session.get('score', 0),
            total_questions=self.total_questions,
            best_score=self.get_top_scores()
        )


if __name__ == '__main__':
    quiz = Quiz(5)
    quiz.start()
