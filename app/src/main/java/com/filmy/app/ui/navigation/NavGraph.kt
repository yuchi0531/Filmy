package com.filmy.app.ui.navigation

import android.net.Uri
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.filmy.app.ui.screen.*

sealed class Screen(val route: String) {
    object Home : Screen("home")
    object Nearby : Screen("nearby")
    object Search : Screen("search")
    object Favorites : Screen("favorites")
    object Settings : Screen("settings")

    object MovieDetail : Screen("movie_detail/{movie_id}")
    object TheaterDetail : Screen("theater_detail/{prefecture}/{area_id}/{theater_id}")
    object WebView : Screen("webview/{url}")

    companion object {
        fun movieDetail(movieId: String): String = "movie_detail/${Uri.encode(movieId)}"

        /** パス引数はすべて URL エンコードする（NavController が自動でデコードする）。 */
        fun theaterDetail(prefecture: String, areaId: String, theaterId: String): String =
            "theater_detail/${Uri.encode(prefecture)}/${Uri.encode(areaId)}/${Uri.encode(theaterId)}"

        /** url はパスに含めるため URL エンコードする（NavController が自動でデコードする）。 */
        fun webView(url: String): String = "webview/${Uri.encode(url)}"
    }
}

@Composable
fun NavGraph(
    navController: NavHostController = rememberNavController(),
    modifier: Modifier = Modifier
) {
    NavHost(
        navController = navController,
        startDestination = Screen.Home.route,
        modifier = modifier
    ) {
        composable(Screen.Home.route) { HomeScreen(navController = navController) }
        composable(Screen.Nearby.route) { NearbyScreen(navController = navController) }
        composable(Screen.Search.route) { SearchScreen(navController = navController) }
        composable(Screen.Favorites.route) { FavoritesScreen(navController = navController) }
        composable(Screen.Settings.route) { SettingsScreen() }

        composable(
            route = Screen.MovieDetail.route,
            arguments = listOf(navArgument("movie_id") { type = NavType.StringType }),
        ) { entry ->
            val movieId = entry.arguments?.getString("movie_id").orEmpty()
            MovieDetailScreen(
                movieId = movieId,
                onNavigateWebView = { url -> navController.navigate(Screen.webView(url)) },
            )
        }

        composable(
            route = Screen.TheaterDetail.route,
            arguments = listOf(
                navArgument("prefecture") { type = NavType.StringType },
                navArgument("area_id") { type = NavType.StringType },
                navArgument("theater_id") { type = NavType.StringType },
            ),
        ) { entry ->
            TheaterDetailScreen(
                prefecture = entry.arguments?.getString("prefecture").orEmpty(),
                areaId = entry.arguments?.getString("area_id").orEmpty(),
                theaterId = entry.arguments?.getString("theater_id").orEmpty(),
                onNavigateWebView = { url -> navController.navigate(Screen.webView(url)) },
            )
        }

        composable(
            route = Screen.WebView.route,
            arguments = listOf(navArgument("url") { type = NavType.StringType }),
        ) { entry ->
            val url = entry.arguments?.getString("url").orEmpty()
            WebViewScreen(
                url = url,
                onBack = { navController.popBackStack() },
            )
        }
    }
}