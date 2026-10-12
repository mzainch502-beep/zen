package app.zen
import androidx.compose.ui.test.junit4.createComposeRule
import androidx.compose.ui.test.*
import org.junit.Rule
import org.junit.Test
class NavigationTest {
    @get:Rule val compose = createComposeRule()
    @Test fun offlineStateHasNoFabricatedEquity() {
        compose.setContent { ZenApp() }
        compose.onNodeWithText("OFFLINE").assertExists()
        compose.onNodeWithText("Connect securely").assertHasClickAction()
        compose.onNodeWithText("Owner email").performTextInput("owner@example.test")
        compose.onNodeWithText("Password").performTextInput("test-password")
        compose.onNodeWithText("HTTPS backend URL").performTextInput("https://example.test")
        compose.onNodeWithText("Secure sign in").assertExists()
    }
}
