import axios from 'axios'

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL
})

export const CHAT_USER_ID = 'facuvega-001'

export const chatService = {
    sendMessage(text, userId = CHAT_USER_ID) {
        return api.post('/chat', {
            contenido: text,
            customerId: userId
        })
    }
}