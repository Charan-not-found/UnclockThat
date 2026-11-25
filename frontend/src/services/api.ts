import axios from 'axios'
// Point to FastAPI later: set VITE_API_URL and flip USE_MOCK to false.
export const USE_MOCK = true
export const api = axios.create({ baseURL: import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api' })
export const delay = (ms: number) => new Promise(r => setTimeout(r, ms))
