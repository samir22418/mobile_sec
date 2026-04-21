package com.aegis.agent.sample.ui

import android.os.Bundle
import android.widget.Toast
import androidx.appcompat.app.AppCompatActivity
import com.aegis.agent.sample.databinding.ActivityMainBinding
import dagger.hilt.android.AndroidEntryPoint
import timber.log.Timber

@AndroidEntryPoint
class MainActivity : AppCompatActivity() {

    private lateinit var binding: ActivityMainBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityMainBinding.inflate(layoutInflater)
        setContentView(binding.root)

        Timber.d("AEGIS Agent Sample started")

        binding.btnStartScan.setOnClickListener {
            Toast.makeText(this, "AEGIS Agent running…", Toast.LENGTH_SHORT).show()
            Timber.d("Scan triggered by user")
        }
    }
}
