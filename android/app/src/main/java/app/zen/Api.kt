package app.zen

import android.content.Context
import android.security.keystore.KeyGenParameterSpec
import android.security.keystore.KeyProperties
import android.util.Base64
import java.security.KeyStore
import javax.crypto.Cipher
import javax.crypto.KeyGenerator
import javax.crypto.SecretKey
import javax.crypto.spec.GCMParameterSpec
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.MediaType.Companion.toMediaType
import org.json.JSONObject
import java.net.URI
import java.util.concurrent.TimeUnit

interface ZenRepository {
    var base: String
    var token: String
    suspend fun call(path: String, method: String = "GET", body: JSONObject? = null): String
    fun clearSession() { token = "" }
}
class ApiFailure(val code: Int, message: String) : Exception(message)

class SessionStore(context: Context) {
    private val prefs = context.getSharedPreferences("zen_private_session", Context.MODE_PRIVATE)
    private fun key(): SecretKey {
        val store = KeyStore.getInstance("AndroidKeyStore").apply { load(null) }
        (store.getKey("zen_session_v1", null) as? SecretKey)?.let { return it }
        return KeyGenerator.getInstance(KeyProperties.KEY_ALGORITHM_AES, "AndroidKeyStore").apply {
            init(KeyGenParameterSpec.Builder("zen_session_v1", KeyProperties.PURPOSE_ENCRYPT or KeyProperties.PURPOSE_DECRYPT)
                .setBlockModes(KeyProperties.BLOCK_MODE_GCM).setEncryptionPaddings(KeyProperties.ENCRYPTION_PADDING_NONE).build())
        }.generateKey()
    }
    fun read(): String = runCatching {
        val encoded = prefs.getString("ciphertext", null) ?: return ""
        val bytes = Base64.decode(encoded, Base64.NO_WRAP)
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.DECRYPT_MODE, key(), GCMParameterSpec(128, bytes.copyOfRange(0, 12)))
        String(cipher.doFinal(bytes.copyOfRange(12, bytes.size)), Charsets.UTF_8)
    }.getOrDefault("")
    fun save(value: String) {
        if (value.isEmpty()) { prefs.edit().remove("ciphertext").apply(); return }
        val cipher = Cipher.getInstance("AES/GCM/NoPadding")
        cipher.init(Cipher.ENCRYPT_MODE, key())
        val encoded = Base64.encodeToString(cipher.iv + cipher.doFinal(value.toByteArray(Charsets.UTF_8)), Base64.NO_WRAP)
        prefs.edit().putString("ciphertext", encoded).apply()
    }
}
class Api(context: Context? = null) : ZenRepository {
    private val store = context?.let { SessionStore(it.applicationContext) }
    override var base = BuildConfig.BACKEND_URL
    override var token: String = store?.read().orEmpty()
        set(value) { field = value; store?.save(value) }
    private val client = OkHttpClient.Builder().connectTimeout(10, TimeUnit.SECONDS).readTimeout(20, TimeUnit.SECONDS)
        .followRedirects(false).followSslRedirects(false).build()
    override suspend fun call(path: String, method: String, body: JSONObject?): String = withContext(Dispatchers.IO) {
        val origin = URI(base)
        require(origin.scheme == "https" && origin.host != null && origin.userInfo == null && origin.query == null && origin.fragment == null) { "Use a valid HTTPS server address" }
        val builder = Request.Builder().url(base.trimEnd('/') + path)
        if (token.isNotEmpty()) builder.header("Authorization", "Bearer $token")
        if (method == "GET") builder.get() else builder.method(method, (body ?: JSONObject()).toString().toRequestBody("application/json".toMediaType()))
        client.newCall(builder.build()).execute().use { response ->
            val text = response.body?.string().orEmpty()
            if (!response.isSuccessful) {
                if (response.code == 401) clearSession()
                val detail = runCatching { JSONObject(text).optString("detail") }.getOrDefault("Request failed")
                throw ApiFailure(response.code, when(response.code) {
                    401 -> if(path=="/auth/login") "The email or password did not match. Please retry." else "Your session has expired. Sign in again."
                    502, 503 -> "This service is temporarily unavailable. Please retry."
                    else -> detail.ifBlank { "Request failed (${response.code})" }
                })
            }
            text
        }
    }
}
