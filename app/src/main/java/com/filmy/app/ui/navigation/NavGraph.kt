package com.filmy.app.ui.navigation

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import com.filmy.app.ui.screen.*

sealed class Screen(val route: String) {
    object Home : Screen("home")
    object Nearby : Screen("nearby")
    object Search : Screen("search")
    object Favorites : Screen("favorites")
    object Settings : Screen("settings")
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
        composable(Screen.Home.route) { HomeScreen() }
        composable(Screen.Nearby.route) { NearbyScreen() }
        composable(Screen.Search.route) { SearchScreen() }
        composable(Screen.Favorites.route) { FavoritesScreen() }
        composable(Screen.Settings.route) { SettingsScreen() }
    }
}
