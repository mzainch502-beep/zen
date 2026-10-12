package app.zen
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.MediaType.Companion.toMediaType
import org.json.JSONObject
import java.net.URI
import java.util.concurrent.TimeUnit

class Api {
    var base = ""
    var token = "" // Memory only. Nothing sensitive is persisted on the phone.
    private val client = OkHttpClient.Builder().connectTimeout(10, TimeUnit.SECONDS).readTimeout(20, TimeUnit.SECONDS).followRedirects(false).build()
    suspend fun call(path: String, method: String = "GET", body: JSONObject? = null): String = withContext(Dispatchers.IO) {
        val origin = URI(base)
        require(origin.scheme == "https" && origin.host != null && origin.userInfo == null && origin.query == null) { "Enter a valid HTTPS backend URL" }
        val builder = Request.Builder().url(base.trimEnd('/') + path)
        if (token.isNotEmpty()) builder.header("Authorization", "Bearer $token")
        if (method == "GET") builder.get() else builder.method(method, (body ?: JSONObject()).toString().toRequestBody("application/json".toMediaType()))
        client.newCall(builder.build()).execute().use { response ->
            val text = response.body?.string() ?: ""
            if (!response.isSuccessful) {
                if (response.code == 401) token = ""
                val detail = runCatching { JSONObject(text).optString("detail") }.getOrDefault("Backend request failed")
                error("${response.code}: $detail")
            }
            text
        }
    }
}
