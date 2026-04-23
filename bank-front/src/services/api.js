import axios from 'axios'

const api = axios.create({
    baseURL: import.meta.env.VITE_API_URL
})

export const CHAT_USER_ID = 'facuvega-001'

export const chatService = {
    /**
     * @param {string} text
     * @param {string} [userId]
     * @param {string} [contexto] — último mensaje del asistente (texto plano) para el router
     */
    sendMessage(text, userId = CHAT_USER_ID, contexto) {
        const body = {
            contenido: text,
            customerId: userId
        }
        if (contexto != null && String(contexto).length > 0) {
            body.contexto = String(contexto)
        }
        return api.post('/chat', body)
    }
}