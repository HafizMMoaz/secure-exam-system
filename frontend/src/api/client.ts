import axios, { type AxiosError, type InternalAxiosRequestConfig } from "axios"

const BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:5500"

const client = axios.create({
  baseURL: BASE_URL,
})

client.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = localStorage.getItem("token")
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      localStorage.removeItem("token")
      localStorage.removeItem("user")
      window.location.href = "/login"
    }
    return Promise.reject(error)
  },
)

export default client
