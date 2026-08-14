package com.filmy.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.filmy.app.ui.navigation.NavGraph
import com.filmy.app.ui.navigation.Screen
import com.filmy.app.ui.theme.FilmyTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            FilmyTheme {
                Surface(modifier = Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    MainScreen()
                }
            }
        }
    }
}

@Composable
fun MainScreen() {
    val navController = rememberNavController()
    val navBackStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = navBackStackEntry?.destination?.route ?: Screen.Home.route

    // 詳細画面（WebView 含む）では下部ナビゲーションバーを非表示にする。
    val isDetailScreen = currentRoute == Screen.MovieDetail.route ||
        currentRoute == Screen.TheaterDetail.route ||
        currentRoute == Screen.WebView.route

    Scaffold(
        bottomBar = {
            if (!isDetailScreen) {
                NavigationBar {
                    val items = listOf(
                        Screen.Home to "Home",
                        Screen.Nearby to "Nearby",
                        Screen.Search to "Search",
                        Screen.Favorites to "Favorites",
                        Screen.Settings to "Settings"
                    )
                    items.forEach { (screen, title) ->
                        NavigationBarItem(
                            icon = {
                                Icon(
                                    imageVector = when (screen) {
                                        Screen.Home -> Icons.Default.Home
                                        Screen.Nearby -> Icons.Default.LocationOn
                                        Screen.Search -> Icons.Default.Search
                                        Screen.Favorites -> Icons.Default.Favorite
                                        else -> Icons.Default.Settings
                                    },
                                    contentDescription = title
                                )
                            },
                        label = { Text(title) },
                        selected = currentRoute == screen.route,
                        onClick = {
                            navController.navigate(screen.route) {
                                popUpTo(navController.graph.startDestinationId) {
                                    saveState = true
                                }
                                launchSingleTop = true
                                restoreState = true
                            }
                        }
                    )
                }
            }
        }
    }
    ) { innerPadding ->
        NavGraph(navController = navController, modifier = Modifier.padding(innerPadding))
    }
}
