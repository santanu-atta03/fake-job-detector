import { useState } from "react";

import JobForm from "./components/JobForm";
import ResultCard from "./components/ResultCard";

import { analyzeJob } from "./services/api";

import "./App.css";


function App() {

    const [result, setResult] = useState(null);

    const [loading, setLoading] = useState(false);

    const [error, setError] = useState("");


    async function handleAnalyze(jobData) {

        setLoading(true);

        setError("");

        setResult(null);


        try {

            const prediction =
                await analyzeJob(jobData);


            setResult(prediction);

        }

        catch (error) {

            console.error(error);

            setError(
                "Unable to analyze the job posting. " +
                "Please make sure the backend server is running."
            );

        }

        finally {

            setLoading(false);
        }
    }


    return (

        <div className="app">

            <header className="hero">

                <div className="hero-icon">
                    🛡️
                </div>

                <h1>
                    Fake Job Detector
                </h1>

                <p>
                    Analyze a job posting for
                    potential fraud using machine
                    learning and explainable AI.
                </p>

            </header>


            <main className="container">

                <section className="form-section">

                    <h2>
                        Analyze a Job Posting
                    </h2>

                    <p className="section-description">

                        Enter the job details below
                        and our ML model will analyze
                        suspicious patterns.

                    </p>


                    <JobForm
                        onAnalyze={
                            handleAnalyze
                        }
                        loading={
                            loading
                        }
                    />

                </section>


                {error && (

                    <div className="error">

                        {error}

                    </div>

                )}


                <ResultCard
                    result={result}
                />

            </main>


            <footer>

                <p>
                    Fake Job Detector •
                    Machine Learning + Explainable AI
                </p>

            </footer>

        </div>
    );
}


export default App;
