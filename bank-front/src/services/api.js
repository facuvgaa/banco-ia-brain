import axios from 'axios'

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL
})

export const chatService = {
    sendMessage(text, userId = "facuvega-001"){
        return api.post('/chat', {
            contenido: text,
            customerId: userId
        })
    }
}